"""
Django admin command to update translations to xblock, mongodb.
"""
import json
from django.core.management.base import BaseCommand
from opaque_keys.edx.keys import UsageKey
from datetime import datetime
from logging import getLogger

from common.lib.xmodule.xmodule.modulestore.django import modulestore
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock
from openedx.features.wikimedia_features.meta_translations.wiki_components import COMPONENTS_CLASS_MAPPING

log = getLogger(__name__)

class Command(BaseCommand):
    """
    This command will check and update translation to the database

        $ ./manage.py cms apply_approved_translations_to_course_blocks
        It will show all updated blocks that are ready for update.

        $ ./manage.py cms apply_approved_translations_to_course_blocks --commit
        It will apply approved translations to course blocks, eventually it updates database.
    """
    
    help = 'Commad to update approved translations to edx course blocks'
    _RESULT = {
        "updated_blocks_count": 0,
        "success_updated_blocks_count": 0
    }

    def add_arguments(self, parser):
        """
        Add --commit argument with default value False
        """
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Send translations to Edx Database',
        )
    
    def _log_final_report(self):
        """
        Log final stats.
        """
        log.info('\n\n\n')
        log.info("--------------------- WIKI TRANSLATION UPDATED BlOCKS STATS - {} ---------------------".format(
            datetime.now().date().strftime("%m-%d-%Y")
        ))
        log.info('Total number of updated blocks: {}'.format(self._RESULT.get("updated_blocks_count")))
        log.info('Total blocks updated successfully: {}'.format(self._RESULT.get("success_updated_blocks_count")))
    
    def _get_json_data_from_translated_blocks(self, translated_course_blocks):
        """
        Extrat version data from translated CourseeBlocks and convert that into json format
        Arguments:
            translated_course_blocks: QuerySet(CourseBlock)
        Returns:
            dict: formated with block keys and their translations
            {
                'block_id_1': {'display_name': 'Section'},
                'block_id_2': {'display_name': 'Unit', 'contect': '<p>...</p>'}
            }
        """
        translations_data = translated_course_blocks.values('block_id', 'applied_version__data')
    
        block_data = {}
        for wikitranslation in translations_data:
            id = str(wikitranslation['block_id'])
            data = wikitranslation['applied_version__data']
            block_data[id] = data
        return block_data
    
    def _update_blocks_data_to_database(self, translated_course_blocks):
        """
        Transport all available transaltions to edx database
        Update applied status of course blocks
        Arguments:
            translated_course_blocks: QuerySet(CourseBlock)
        """
        success_count = 0
        for course_block in translated_course_blocks:
            data = course_block.applied_version.data
            block_location = course_block.block_id
            block =  modulestore().get_item(block_location)
            updated_block = COMPONENTS_CLASS_MAPPING[block_location.block_type]().update(block, data)
            if (updated_block):
                course_block.applied_translation = True
                course_block.save()
                success_count += 1
        
        self._RESULT.update({
                     "success_updated_blocks_count": success_count
                })
    
    def handle(self, *args, **options):
        translated_course_blocks = CourseBlock.objects.filter(
            applied_translation=False,
            applied_version__isnull=False
        )
        if options.get('commit'):
            self._RESULT.update({"updated_blocks_count": len(translated_course_blocks)})
            if translated_course_blocks:
                self._update_blocks_data_to_database(translated_course_blocks)
            else:
                log.info('No Transaltions found to update')
            self._log_final_report()
        else:
            blocks_data = self._get_json_data_from_translated_blocks(translated_course_blocks)
            log.info(json.dumps(blocks_data, indent=4)) 
