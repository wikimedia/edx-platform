from logging import getLogger
from lxml import etree

from django.core.management.base import BaseCommand
from django.core import management

from common.lib.xmodule.xmodule.modulestore.django import modulestore

from openedx.features.wikimedia_features.meta_translations.models import (
    CourseBlockData,
    CourseBlock,
    TranslationVersion,
    WikiTranslation,
)
from openedx.features.wikimedia_features.meta_translations.transformers.wiki_transformer import (
    ProblemTransformer,
)

from opaque_keys.edx.keys import UsageKey


log = getLogger(__name__)


class Command(BaseCommand):
    """
    This command is supposed to run if the parsing rules have changed in ProblemTransformer. It will update parsed_keys in CourseBlockData and reset the translation for every corresponding target block.

    ./manage.py cms apply_wiki_parsing_changes
    """

    help = "Update CourseBlockData entries text input problem blocks."

    def _are_parsed_keys_changed(self, old_parsed_keys, new_parsed_keys):
        return old_parsed_keys.keys() != new_parsed_keys.keys()

    def _update_base_course_blocks_data(self, base_course_blocks_data):
        """Updates parsed_keys and data in CourseBlockData if the parsing rules have changed in ProblemTransformer.

        Args:
            base_course_blocks_data (queryset): queryset of CourseBlockData

        Returns:
            list: base course block ids for updated CourseBlockData.
        """
        updated_course_blocks_data = []

        for course_block_data in base_course_blocks_data:
            block_id = UsageKey.from_string(str(course_block_data.course_block.block_id))

            try:
                block = modulestore().get_item(block_id)
            except Exception:
                # Incase there is a disconnected block. Shouldn't happen though in normal case.
                log.info("Missing block: {}".format(course_block_data.course_block.block_id))
                continue

            parsed_keys = ProblemTransformer().raw_data_to_meta_data(block.data)

            if self._are_parsed_keys_changed(course_block_data.parsed_keys, parsed_keys):
                # Update CourseBlockData data and parsed_keys.
                course_block_data.data = block.data
                course_block_data.parsed_keys = parsed_keys
                course_block_data.content_updated = True
                course_block_data.save()

                updated_course_blocks_data.append(course_block_data.id)
                log.info("Updated CourseBlockData for block: {}".format(course_block_data.course_block.block_id))

        return updated_course_blocks_data

    def _unset_old_translations(self, updated_course_blocks_data):
        """Resets the translations for all translated rerun courses.

        Args:
            updated_course_blocks_data (list): base course block ids for updated CourseBlockData.
        """
        # get the block ids of all translated rerun courses.
        target_block_ids = (
            WikiTranslation.objects.filter(source_block_data__in=updated_course_blocks_data)
            .values_list("target_block__block_id", flat=True)
            .distinct()
        )
        target_block_ids = [str(block_id) for block_id in target_block_ids]

        updated_wiki_trans = WikiTranslation.objects.filter(target_block__block_id__in=target_block_ids).update(
            approved=False, approved_by=None
        )

        updated_course_blocks = CourseBlock.objects.filter(block_id__in=target_block_ids).update(
            translated=False, applied_version=None, applied_translation=False
        )

        deleted_trans_ver = TranslationVersion.objects.filter(block_id__in=target_block_ids).delete()

        log.info("Updated {} CourseBlocks and {} WikiTranslations.".format(updated_course_blocks, updated_wiki_trans))
        log.info("Deleted {} translation versions.".format(deleted_trans_ver))

    def _run_send_and_fetch_jobs(self):
        management.call_command("sync_untranslated_strings_to_meta_from_edx", commit=True)
        management.call_command("sync_translated_strings_to_edx_from_meta", commit=True)

    def handle(self, *args, **options):
        # get CourseBlockData entries to update
        course_blocks_data = CourseBlockData.objects.select_related("course_block").filter(
            course_block__block_type="problem",
            data_type="content",
        )

        updated_course_blocks_data = self._update_base_course_blocks_data(course_blocks_data)

        if updated_course_blocks_data:
            self._unset_old_translations(updated_course_blocks_data)
            self._run_send_and_fetch_jobs()

        log.info("No. of blocks updated: {}".format(len(updated_course_blocks_data)))
