from django.core.management.base import BaseCommand

from openedx.features.wikimedia_features.meta_translations.models import CourseBlockData

from opaque_keys.edx.keys import CourseKey

from logging import getLogger

log = getLogger(__name__)

class Command(BaseCommand):
    """
    This command will set mapped_true flag to true in all course_block_data entries to mark them for syncing.
    This command it supposed to run before syncing message bundle to meta server in case there's a change to message  bundle structure.

    ./manage.py cms mark_translations_for_sync
    ./manage.py cms mark_translations_for_sync course_id_1 course_id_2
    """
    help = "Marks all CourseBlockData entries to be synced to meta server."

    def add_arguments(self, parser):
        parser.add_argument("course_ids", nargs="*", type=str, help="Provide list of course ids. If not provided, all courses will be synced.")

    def handle(self, *args, **options):
        if (options["course_ids"]):
            course_keys = map(lambda x: CourseKey.from_string(x), options["course_ids"])
            count = CourseBlockData.objects.filter(course_block__course_id__in=course_keys).update(mapping_updated=True)
            log.info(f'Updated {count} CourseBlockData entries across the provided courses.')
        else:
            CourseBlockData.objects.all().update(mapping_updated=True)
            log.info("Updated all CourseBlockData entries across all courses.")
