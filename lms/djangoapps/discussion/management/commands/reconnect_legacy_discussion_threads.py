"""
Management command to reconnect orphaned legacy discussion-XBlock threads to the
new in-context (forum v2 / ``openedx`` provider) discussion topics.

Background
----------
Courses authored with legacy inline ``discussion`` XBlocks store their threads in
the forum under the XBlock's ``discussion_id`` (a hash, used as the forum
``commentable_id``). When such a course is switched to the ``openedx`` in-context
provider, ``DiscussionTopicLink`` rows are created with freshly generated
``uuid4()`` external ids (see ``discussions/handlers.py``) that do **not** reuse the
legacy ``discussion_id``. The existing threads therefore point at commentable ids
that no topic references, so they disappear from units, from the Discussions MFE
"Topics" list, and their counts read zero. Graded units get no topic link at all
unless ``DiscussionsConfiguration.enable_graded_units`` is set (``discussions/tasks.py``).

There is no upstream migration for this -- upstream's own migration deletes and
recreates topic links with new UUIDs, so it does not reconnect existing threads.

What this command does (per ``openedx``-provider course)
--------------------------------------------------------
For every commentable that actually has threads but is not referenced by any topic
link:

* If the parent unit already has a topic link, point its ``external_id`` at the
  legacy ``discussion_id`` (a swap; preserved across re-publish because per-unit
  topic contexts carry no ``external_id`` -- see ``handlers.py``).
* If the unit has no link (typically a graded unit), create an enabled link with the
  legacy ``discussion_id`` and set ``enable_graded_units=True`` on the course config
  so the link survives re-publish (matches upstream's intent for discussion XBlocks
  in graded subsections).
* Anything that cannot be mapped 1:1 to a unit (a unit with two posted-in XBlocks,
  or a commentable whose XBlock no longer exists) is registered as a course-level
  topic so the threads remain reachable, and is reported rather than clobbered.

For **every** course that has threads -- whether or not any topics needed reconnecting
-- it also seeds ``ForumUser`` records for enrolled users and recomputes per-course user
stats, so the "Learners" tab populates. (The Mongo->MySQL migration brings threads but
not ``ForumUser`` records, and the stats read does ``ForumUser.objects.get()`` per
stat-bearing user, so a missing record otherwise makes the endpoint fail.) It performs
only Django-model writes (``DiscussionsConfiguration`` / ``DiscussionTopicLink`` /
``ForumUser``) plus the stats recompute -- no modulestore/content writes and no
forum thread/comment writes -- so it is reversible.

Invoke with (dry-run by default)::

    python manage.py lms reconnect_legacy_discussion_threads course-v1:ORG+NUM+RUN
    python manage.py lms reconnect_legacy_discussion_threads all
    python manage.py lms reconnect_legacy_discussion_threads all --apply --reindex
"""
import logging

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from opaque_keys.edx.keys import CourseKey

import openedx.core.djangoapps.django_comment_common.comment_client as cc
from common.djangoapps.student.models import CourseEnrollment
from openedx.core.djangoapps.discussions.models import DiscussionsConfiguration, DiscussionTopicLink
from openedx.core.djangoapps.django_comment_common.comment_client.course import (
    get_course_commentable_counts,
    update_course_users_stats,
)
from xmodule.modulestore.django import modulestore

log = logging.getLogger(__name__)

PROVIDER = "openedx"


class Command(BaseCommand):
    help = "Reconnect orphaned legacy discussion-XBlock threads to in-context discussion topics."

    def add_arguments(self, parser):
        parser.add_argument(
            "course_ids",
            nargs="*",
            help="One or more course ids, or 'all' (or no argument) to scan every "
                 "openedx-provider course.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write changes. Without this flag the command runs as a dry-run and only reports.",
        )
        parser.add_argument(
            "--reindex",
            action="store_true",
            help="After processing, rebuild the forum search index once (global). "
                 "Only meaningful with --apply.",
        )

    def handle(self, *args, **options):
        self.store = modulestore()
        self.apply = options["apply"]
        course_ids = options["course_ids"]

        self.stdout.write(f"MODE: {'APPLY' if self.apply else 'DRY-RUN'}")
        course_keys = self._discover(course_ids)
        self.stdout.write(f"Scanning {len(course_keys)} course(s)\n")

        summary = []
        for course_key in course_keys:
            try:
                result = self._process_course(course_key)
                if result:
                    summary.append(result)
            except Exception as exc:  # pylint: disable=broad-except
                log.exception("Failed processing %s", course_key)
                self.stderr.write(f"  !! {course_key}: {type(exc).__name__}: {exc}")
                summary.append({"course": str(course_key), "status": "error", "error": str(exc)})

        self.stdout.write("\n==== SUMMARY ====")
        for result in summary:
            self.stdout.write(str(result))

        if self.apply and options["reindex"]:
            self.stdout.write("\nRebuilding forum search index (global)...")
            call_command("rebuild_forum_indices")
        elif not options["reindex"]:
            self.stdout.write(
                "\nReminder: rebuild the forum search index once after applying:\n"
                "  python manage.py lms rebuild_forum_indices"
            )

    def _discover(self, course_ids):
        if course_ids and "all" not in course_ids:
            return [CourseKey.from_string(c) for c in course_ids]
        return list(
            DiscussionsConfiguration.objects
            .filter(provider_type=PROVIDER, enabled=True)
            .values_list("context_key", flat=True)
            .distinct()
        )

    def _unit_hierarchy(self, unit_key):
        """Return (graded, context-dict) for a vertical, walking up to subsection/section."""
        try:
            unit = self.store.get_item(unit_key)
            subsection = self.store.get_item(unit.parent)
            section = self.store.get_item(subsection.parent)
            return bool(getattr(subsection, "graded", False)), {
                "section": section.display_name,
                "subsection": subsection.display_name,
                "unit": unit.display_name,
            }
        except Exception:  # pylint: disable=broad-except
            return False, {}

    def _build_xblock_map(self, course_key):
        """discussion_id -> {unit_key, title} for every legacy discussion XBlock in the course."""
        xmap = {}
        for block in self.store.get_items(course_key, qualifiers={"category": "discussion"}):
            discussion_id = getattr(block, "discussion_id", None)
            parent = getattr(block, "parent", None)
            if not discussion_id or parent is None or parent.block_type != "vertical":
                continue
            title = (getattr(block, "discussion_target", None)
                     or getattr(block, "discussion_category", None)
                     or getattr(block, "display_name", None)
                     or "Discussion")
            xmap[discussion_id] = {"unit_key": parent, "title": title}
        return xmap

    def _process_course(self, course_key):
        config = DiscussionsConfiguration.get(context_key=course_key)
        if config.provider_type != PROVIDER:
            return None

        counts = get_course_commentable_counts(course_key) or {}
        active = {cid for cid, c in counts.items() if sum((c or {}).values()) > 0}
        if not active:
            return {"course": str(course_key), "status": "no-threads"}

        links = list(DiscussionTopicLink.objects.filter(context_key=course_key, provider_id=PROVIDER))
        linked_external_ids = {link.external_id for link in links}
        orphans = active - linked_external_ids

        xmap = self._build_xblock_map(course_key)
        links_by_unit = {link.usage_key: link for link in links if link.usage_key}
        next_order = (max((link.ordering or 0) for link in links) + 1) if links else 100
        units_taken = set()
        need_graded = False
        plan = []  # list of (kind, external_id, detail)

        for external_id in sorted(orphans):
            info = xmap.get(external_id)
            if not info:
                plan.append(("course-topic", external_id, f"orphan {external_id[:8]} (no current XBlock)"))
                continue

            unit = info["unit_key"]
            link = links_by_unit.get(unit)
            if unit in units_taken:
                plan.append(("course-topic", external_id, f"{info['title']} (unit already mapped)"))
            elif link:
                if link.external_id in active and link.external_id != external_id:
                    plan.append(("course-topic", external_id,
                                 f"{info['title']} (unit topic {link.external_id[:8]} has its own posts)"))
                else:
                    plan.append(("swap", external_id,
                                 f"{info['title']} -> unit {unit.block_id[:8]} (was {link.external_id[:8]})"))
                    units_taken.add(unit)
            else:
                graded, _ = self._unit_hierarchy(unit)
                need_graded = need_graded or graded
                plan.append(("unit-topic", external_id,
                             f"{info['title']} -> NEW link on unit {unit.block_id[:8]} (graded={graded})"))
                units_taken.add(unit)

        self.stdout.write(
            f"\n=== {course_key} ===  threads={len(active)} orphaned-commentables={len(orphans)}"
        )
        for kind, external_id, detail in plan:
            self.stdout.write(f"  [{kind:12}] {external_id}  {detail}")
        if need_graded and not config.enable_graded_units:
            self.stdout.write("  [config      ] set enable_graded_units = True")

        if not self.apply:
            self.stdout.write("  (dry-run: no changes written)")
            status = "would-fix" if plan else "would-refresh-stats"
            return {"course": str(course_key), "status": status, "actions": len(plan)}

        if need_graded and not config.enable_graded_units:
            config.enable_graded_units = True
            config.save()

        for kind, external_id, _ in plan:
            if kind == "swap":
                link = links_by_unit[xmap[external_id]["unit_key"]]
                link.external_id = external_id
                link.enabled_in_context = True
                link.save()
            elif kind == "unit-topic":
                unit = xmap[external_id]["unit_key"]
                _, context = self._unit_hierarchy(unit)
                DiscussionTopicLink.objects.create(
                    context_key=course_key, usage_key=unit, provider_id=PROVIDER,
                    external_id=external_id, title=xmap[external_id]["title"],
                    enabled_in_context=True, ordering=next_order, context=context,
                )
                next_order += 1
            elif kind == "course-topic":
                title = (xmap[external_id]["title"] if external_id in xmap
                         else f"Archived discussion {external_id[:8]}")
                DiscussionTopicLink.objects.create(
                    context_key=course_key, usage_key=None, provider_id=PROVIDER,
                    external_id=external_id, title=title,
                    enabled_in_context=True, ordering=next_order, context={},
                )
                next_order += 1

        seeded = self._seed_forum_users(course_key)
        update_course_users_stats(course_key)
        self.stdout.write(f"  -> applied; seeded {seeded} forum users; user stats recomputed")
        status = "fixed" if plan else "stats-refreshed"
        return {"course": str(course_key), "status": status, "actions": len(plan), "seeded_users": seeded}

    def _seed_forum_users(self, course_key):
        """
        Ensure every enrolled user has a ForumUser record.

        The Mongo->MySQL migration brings threads but not user records, and the forum's
        per-course stats read does ``ForumUser.objects.get(...)`` for each stat-bearing
        user -- a single missing record makes the Learners endpoint fail. Seeding here
        keeps ``update_course_users_stats`` (called next) from producing stats that the
        read path then chokes on.
        """
        users = User.objects.filter(
            courseenrollment__course_id=course_key,
            courseenrollment__is_active=True,
        ).distinct()
        seeded = 0
        for user in users:
            try:
                cc.User.from_django_user(user).save()
                seeded += 1
            except Exception as exc:  # pylint: disable=broad-except
                log.warning("Failed to seed forum user %s: %s", user.username, exc)
        return seeded
