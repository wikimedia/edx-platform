"""
Management command to repair corrupted static asset URLs in course block content.

It heals two distinct, related corruptions of non-ASCII asset filenames:

1. Multiply percent-encoded links. A non-idempotent call to
   ``StaticContent.get_canonicalized_asset_path`` used to re-encode already-encoded
   asset paths on every Studio load/save cycle, so a file named "Día.jpg" (whose
   ``í`` is UTF-8 ``%C3%AD``) degraded into ``%25C3%25AD``, then ``%2525C3%2525AD``,
   and so on. These are recoverable by fully decoding the percent-encoding.

2. Dropped-character links. In some content (typically from an older import) the
   non-ASCII character was stripped entirely rather than encoded, e.g.
   "climática" became "climtica", so the link points at a filename that does not
   exist while the real asset still carries the accent. These are recovered by
   matching the broken reference against the course's real assets: the asset
   whose name, with non-ASCII characters removed, equals the broken reference is
   the intended target.

For every data-bearing block the command fully decodes any static/asset URL,
rewrites absolute asset links (asset-v1:/c4x/versioned) belonging to the course
back to the portable ``/static/<filename>`` form, and -- when the decoded target
does not exist in the course -- repoints it at the matching real asset. Broken
references with no unique match are reported but left untouched for manual review.

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
from xmodule.contentstore.django import contentstore
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

STATIC_PREFIX = '/static/'


def fully_unquote(value):
    """Percent-decode ``value`` repeatedly until it stops changing."""
    prev = None
    while prev != value:
        prev = value
        value = unquote(value)
    return value


def ascii_fold(name):
    """Return ``name`` with all non-ASCII characters removed.

    This mirrors the corruption that dropped accented characters from asset
    references, so folding a real asset name reproduces its broken reference.
    """
    return name.encode('ascii', 'ignore').decode('ascii')


class AssetIndex:
    """Lookup over a course's real asset filenames (asset key block_ids)."""

    def __init__(self, block_ids):
        self.names = set(block_ids)
        # Map the ASCII-folded form of each real name to the set of real names
        # that fold to it, so a dropped-character reference can be matched back.
        self.by_ascii = {}
        for name in self.names:
            self.by_ascii.setdefault(ascii_fold(name), set()).add(name)

    @classmethod
    def for_course(cls, course_key):
        """Build an index from the course's contentstore assets."""
        assets, __ = contentstore().get_all_content_for_course(course_key)
        return cls(asset['asset_key'].block_id for asset in assets)

    def resolve(self, filename):
        """
        Resolve a referenced ``filename`` against the real assets.

        Returns a ``(status, realname)`` tuple:
          * ('ok', filename)        the asset exists as referenced
          * ('matched', realname)   a single asset matches once accents are
                                    dropped -- the intended target
          * ('ambiguous', None)     more than one asset matches; needs review
          * ('unmatched', None)     no asset matches; needs review
        """
        if filename in self.names:
            return ('ok', filename)
        candidates = {name for name in self.by_ascii.get(ascii_fold(filename), set()) if name != filename}
        if len(candidates) == 1:
            return ('matched', next(iter(candidates)))
        if len(candidates) > 1:
            return ('ambiguous', None)
        return ('unmatched', None)


def _to_portable(decoded, course_key):
    """
    Reduce a decoded asset URL to its portable ``/static/<filename>`` form.

    Returns the portable path for /static/ links and for absolute asset links
    that belong to ``course_key``; returns ``None`` for anything that should be
    left as-is (links to other courses, unparseable links).
    """
    lowered = decoded.lower()
    if lowered.startswith('/static/'):
        return STATIC_PREFIX + decoded[len('/static/'):]
    if lowered.startswith('static/'):
        return STATIC_PREFIX + decoded[len('static/'):]

    # Absolute asset link: try to parse it back into an AssetKey. The serving
    # form uses "block/"; AssetKey wants "block@".
    candidate = decoded.lstrip('/')
    if StaticContent.is_versioned_asset_path('/' + candidate):
        _, candidate = StaticContent.parse_versioned_asset_path('/' + candidate)
        candidate = candidate.lstrip('/')
    candidate = candidate.replace('block/', 'block@')

    try:
        asset_key = AssetKey.from_string(candidate)
    except InvalidKeyError:
        return None

    if asset_key.course_key.for_branch(None) != course_key.for_branch(None):
        return None

    return StaticContent.get_static_path_from_location(asset_key)


def normalize_asset_url(url, course_key, asset_index=None):
    """
    Return ``(new_url, status)`` for a single asset ``url``.

    The percent-encoding is fully decoded and course-owned absolute links are
    reduced to the portable ``/static/<filename>`` form. When ``asset_index`` is
    provided and the decoded target is missing, the link is repointed at the
    matching real asset. ``status`` is one of ``None`` (no asset check / target
    exists), ``'matched'``, ``'ambiguous'`` or ``'unmatched'``.
    """
    decoded = fully_unquote(url)
    portable = _to_portable(decoded, course_key)
    if portable is None:
        # Link to another course or unparseable: keep it decoded, untouched.
        return decoded, None
    if asset_index is None:
        return portable, None

    filename = portable[len(STATIC_PREFIX):]
    status, realname = asset_index.resolve(filename)
    if status == 'matched':
        return STATIC_PREFIX + realname, 'matched'
    if status in ('ambiguous', 'unmatched'):
        return portable, status
    return portable, None


def repair_text(data, course_key, asset_index=None):
    """
    Repair all asset URLs in ``data``.

    Returns ``(new_data, replacements, warnings)`` where ``replacements`` is a
    list of ``(old, new)`` pairs that changed and ``warnings`` is a list of
    ``(url, status)`` pairs for broken references with no unique match.
    """
    replacements = []
    warnings = []

    def _replace(match):
        quote = match.group('quote')
        url = match.group('url')
        new_url, status = normalize_asset_url(url, course_key, asset_index)
        if status in ('ambiguous', 'unmatched'):
            warnings.append((url, status))
        if new_url != url:
            replacements.append((url, new_url))
        return quote + new_url + quote

    new_data = ASSET_URL_RE.sub(_replace, data)
    return new_data, replacements, warnings


class Command(BaseCommand):
    """Repair corrupted static asset URLs in course content."""

    help = (
        "Decode over-encoded static asset URLs and repoint dropped-character "
        "links at their real assets. Runs as a dry run unless --commit is given."
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
        totals = {'blocks': 0, 'urls': 0, 'unresolved': 0}

        for course_key in course_keys:
            self.stdout.write(f"Scanning {course_key} ...")
            with store.bulk_operations(course_key):
                self._repair_course(course_key, commit, totals)

        verb = "Repaired" if commit else "Would repair"
        self.stdout.write(
            f"\n{verb} {totals['urls']} URL(s) across {totals['blocks']} block(s)."
        )
        if totals['unresolved']:
            self.stdout.write(
                f"{totals['unresolved']} broken reference(s) had no unique match "
                "and were left untouched (see WARN lines above)."
            )
        if not commit and (totals['urls'] or totals['unresolved']):
            self.stdout.write("Dry run only. Re-run with --commit to apply.")

    def _repair_course(self, course_key, commit, totals):
        """Repair every data-bearing block in a single course."""
        store = modulestore()
        user_id = ModuleStoreEnum.UserID.mgmt_command
        asset_index = AssetIndex.for_course(course_key)

        for block in store.get_items(course_key):
            data = getattr(block, 'data', None)
            if not isinstance(data, str) or not data:
                continue

            new_data, replacements, warnings = repair_text(data, course_key, asset_index)
            if not replacements and not warnings:
                continue

            if replacements or warnings:
                self.stdout.write(f"  {block.location}")
            for old, new in replacements:
                self.stdout.write(f"    - {old}")
                self.stdout.write(f"    + {new}")
            for url, status in warnings:
                self.stdout.write(f"    ! WARN ({status}, no fix applied): {url}")

            totals['urls'] += len(replacements)
            totals['unresolved'] += len(warnings)
            if replacements:
                totals['blocks'] += 1

            if commit and replacements:
                block.data = new_data
                store.update_item(block, user_id)
                # Push the repaired draft to the published branch so the LMS
                # serves the fixed links. Blocks with no published version
                # (e.g. unpublished drafts) are skipped silently.
                try:
                    store.publish(block.location, user_id)
                except Exception as err:  # lint-amnesty, pylint: disable=broad-except
                    self.stderr.write(f"    ! could not publish {block.location}: {err}")
