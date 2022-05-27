"""
Django admin command to update translations to xblock, mongodb.
"""
import json
from django.core.management.base import BaseCommand
from opaque_keys.edx.keys import UsageKey
from datetime import datetime
from logging import getLogger

from common.lib.xmodule.xmodule.modulestore.django import modulestore
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock, WikiTranslation
from openedx.features.wikimedia_features.meta_translations.wiki_components import COMPONENTS_CLASS_MAPPING

log = getLogger(__name__)

class Command(BaseCommand):
    """
    This command will check and update wikitransaltions to database

        $ ./manage.py cms apply_approved_translations_to_course_blocks
        It will show all updated blocks that are ready for update.

        $ ./manage.py cms apply_approved_translations_to_course_blocks --commit
        It will apply approved wikitranslations to course blocks, eventually it updates database.
    """
    
    help = 'Commad to update approved wikitranslations to edx course blocks'
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
            help='Send WikiTranslations to Edx Database',
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
    
    def _get_blocks_data_from_wikitransaltions(self):
        """
        Find all valid wikitransaltions and reformat it to required format
        {
            'block_id_1': {'display_name': 'Section'},
            'block_id_2': {'display_name': 'Unit', 'contect': '<p>...</p>'}
        }
        Returns:
            dict: formated with block keys and their translations
        """
        translations = WikiTranslation.objects.filter(applied=False, approved=True).values(
            'target_block__block_id', 'source_block_data__data_type', 'translation'
        )
        block_data = {}
        for wikitranslation in translations:
            id = str(wikitranslation['target_block__block_id'])
            data_type = wikitranslation['source_block_data__data_type']
            translation = wikitranslation['translation']
            if id in block_data:
                block_data[id][data_type] = translation
            else:
                block_data[id] = { data_type: translation }
        return block_data
    
    def _update_blocks_data_to_database(self, blocks_data):
        """
        Transport all available wikitranslations to edx database
        Update approved status of translations
        """
        success_count = 0
        for block_id in blocks_data.keys():
            data = blocks_data[block_id]
            block_location = UsageKey.from_string(block_id)
            block =  modulestore().get_item(block_location)
            updated_block = COMPONENTS_CLASS_MAPPING[block_location.block_type]().update(block, data)
            if (updated_block):
                course_block = CourseBlock.objects.get(block_id=block_id)
                course_block.apply_all_translations()
                success_count += 1
        
        self._RESULT.update({
                     "success_updated_blocks_count": success_count
                })
    
    def handle(self, *args, **options):
        blocks_data = self._get_blocks_data_from_wikitransaltions()
        if options.get('commit'):
            self._RESULT.update({"updated_blocks_count": len(blocks_data)})
            if blocks_data:
                self._update_blocks_data_to_database(blocks_data)
            else:
                log.info('No WikiTranslations found to update')
            self._log_final_report()
        else:
            log.info(json.dumps(blocks_data, indent=4)) 
