"""
Management command to repair multiply percent-encoded static asset URLs in
course block content.

A non-idempotent call to ``StaticContent.get_canonicalized_asset_path`` used to
re-encode already-encoded asset paths on every Studio load/save cycle. This
degraded non-ASCII asset filenames, e.g. a file named "Día.jpg" (whose ``í`` is
UTF-8 ``%C3%AD``) would turn into ``%25C3%25AD``, then ``%2525C3%2525AD`` and so
on, leaving broken <img> links in unit HTML.

This command scans the data-bearing blocks of one or more courses, fully decodes
the percent-encoding of any static/asset URLs it finds, and rewrites absolute
asset links (asset-v1:/c4x/versioned) belonging to the course back to the
portable ``/static/<filename>`` form. The platform fix makes canonicalization
idempotent going forward; this command heals content already stored corrupted.

Run from the command line, e.g.:

    ./manage.py cms repair_asset_url_encoding course-v1:Org+Course+Run
    ./manage.py cms repair_asset_url_encoding --all
    ./manage.py cms repair_asset_url_encoding course-v1:Org+Course+Run --commit

Without ``--commit`` the command runs as a dry run and only reports what it
would change.
"""

import re
from urllib.parse import unquote

from django.core.management.base import BaseCommand, CommandError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import AssetKey, CourseKey

from xmodule.contentstore.content import StaticContent
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore

# Matches a quoted URL that points at a static asset, in any of the forms that
# can appear in stored block data: the portable /static/ form, the canonical
# asset-v1: key, the legacy c4x/ key, or a versioned /assets/courseware/ path.
ASSET_URL_RE = re.compile(
    r"""(?P<quote>['"])"""
    r"""(?P<url>/?(?:asset-v1:|c4x/|assets/courseware/|static/)[^'"]*?)"""
    r"""(?P=quote)""",
    re.IGNORECASE | re.VERBOSE,
)


def fully_unquote(value):
    """Percent-decode ``value`` repeatedly until it stops changing."""
    prev = None
    while prev != value:
        prev = value
        value = unquote(value)
    return value


def normalize_asset_url(url, course_key):
    """
    Return the repaired form of a single asset ``url``.

    The percent-encoding is fully stripped. Absolute asset links that belong to
    ``course_key`` are converted back to the portable ``/static/<filename>``
    form; everything else is returned fully decoded but otherwise untouched.
    """
    decoded = fully_unquote(url)

    # Already portable: nothing to convert, just keep it fully decoded.
    static_marker = '/static/'
    lowered = decoded.lower()
    if lowered.startswith('/static/') or lowered.startswith('static/'):
        idx = lowered.find(static_marker)
        return static_marker + decoded[idx + len(static_marker):] if idx != -1 \
            else '/static/' + decoded.split('static/', 1)[1]

    # Absolute asset link: try to parse it back into an AssetKey so we can emit
    # a portable path. The serving form uses "block/"; AssetKey wants "block@".
    candidate = decoded.lstrip('/')
    if StaticContent.is_versioned_asset_path('/' + candidate):
        _, candidate = StaticContent.parse_versioned_asset_path('/' + candidate)
        candidate = candidate.lstrip('/')
    candidate = candidate.replace('block/', 'block@')

    try:
        asset_key = AssetKey.from_string(candidate)
    except InvalidKeyError:
        # Couldn't understand it; leave it fully decoded but don't reshape it.
        return decoded

    # Only portablize assets that actually belong to this course.
    if asset_key.course_key.for_branch(None) != course_key.for_branch(None):
        return decoded

    return StaticContent.get_static_path_from_location(asset_key)


def repair_text(data, course_key):
    """
    Repair all asset URLs in ``data``.

    Returns a ``(new_data, replacements)`` tuple where ``replacements`` is a
    list of ``(old, new)`` pairs for the URLs that actually changed.
    """
    replacements = []

    def _replace(match):
        quote = match.group('quote')
        url = match.group('url')
        new_url = normalize_asset_url(url, course_key)
        if new_url != url:
            replacements.append((url, new_url))
        return quote + new_url + quote

    new_data = ASSET_URL_RE.sub(_replace, data)
    return new_data, replacements


class Command(BaseCommand):
    """Repair multiply percent-encoded static asset URLs in course content."""

    help = (
        "Fully decode and re-portablize over-encoded static asset URLs in "
        "course block content. Runs as a dry run unless --commit is given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'course_keys',
            nargs='*',
            help="One or more course ids to repair (omit when using --all).",
        )
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all_courses',
            help="Repair every course in the modulestore.",
        )
        parser.add_argument(
            '--commit',
            action='store_true',
            help="Persist and publish the changes. Without it, dry-run only.",
        )

    def handle(self, *args, **options):
        store = modulestore()

        if options['all_courses']:
            if options['course_keys']:
                raise CommandError("Don't pass course ids together with --all.")
            course_keys = [course.id for course in store.get_course_summaries()]
        else:
            if not options['course_keys']:
                raise CommandError("Provide at least one course id, or use --all.")
            course_keys = []
            for raw_key in options['course_keys']:
                try:
                    course_keys.append(CourseKey.from_string(raw_key))
                except InvalidKeyError as err:
                    raise CommandError(f"Invalid course key: {raw_key}") from err

        commit = options['commit']
        total_blocks = 0
        total_urls = 0

        for course_key in course_keys:
            self.stdout.write(f"Scanning {course_key} ...")
            with store.bulk_operations(course_key):
                blocks_changed, urls_changed = self._repair_course(course_key, commit)
            total_blocks += blocks_changed
            total_urls += urls_changed

        verb = "Repaired" if commit else "Would repair"
        self.stdout.write(
            f"\n{verb} {total_urls} URL(s) across {total_blocks} block(s)."
        )
        if not commit and total_urls:
            self.stdout.write("Dry run only. Re-run with --commit to apply.")

    def _repair_course(self, course_key, commit):
        """Repair every data-bearing block in a single course."""
        store = modulestore()
        user_id = ModuleStoreEnum.UserID.mgmt_command
        blocks_changed = 0
        urls_changed = 0

        for block in store.get_items(course_key):
            data = getattr(block, 'data', None)
            if not isinstance(data, str) or not data:
                continue

            new_data, replacements = repair_text(data, course_key)
            if not replacements:
                continue

            blocks_changed += 1
            urls_changed += len(replacements)
            self.stdout.write(f"  {block.location}")
            for old, new in replacements:
                self.stdout.write(f"    - {old}")
                self.stdout.write(f"    + {new}")

            if commit:
                block.data = new_data
                store.update_item(block, user_id)
                # Push the repaired draft to the published branch so the LMS
                # serves the fixed links. Blocks with no published version
                # (e.g. unpublished drafts) are skipped silently.
                try:
                    store.publish(block.location, user_id)
                except Exception as err:  # lint-amnesty, pylint: disable=broad-except
                    self.stderr.write(f"    ! could not publish {block.location}: {err}")

        return blocks_changed, urls_changed
