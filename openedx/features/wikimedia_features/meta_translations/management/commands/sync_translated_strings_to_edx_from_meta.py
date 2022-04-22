"""
Django admin command to send untranslated data to Meta Wiki.
"""
import asyncio
import aiohttp
import json
from logging import getLogger
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from opaque_keys.edx.keys import CourseKey, UsageKey

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import (
    WikiTranslation, CourseTranslation, CourseBlock, CourseBlockData
)
from openedx.features.wikimedia_features.meta_translations.meta_client import WikiMetaClient

log = getLogger(__name__)


class Command(BaseCommand):
    """
    This command will check and send updated block strings to meta server for translations.

        $ ./manage.py cms sync_translated_strings_to_edx_from_meta
        It will only show all blocks that are ready to fetched from meta.

        $ ./manage.py cms sync_translated_strings_to_edx_from_meta --commit
        It will send API calls of Wiki Meta to fetch updated translations from meta.
    """
    help = 'Command to sync/fetch updated translations from meta to edX'
    _RESULT = {

    }

    def add_arguments(self, parser):
        """
        Add --commit argument with default value False
        """
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Send API calls to Meta wiki',
        )

    def _log_final_report(self):
        """
        Log final stats.
        """
        log.info('\n\n\n')
        log.info("--------------------- WIKI META UPDATED PAGES STATS - {} ---------------------".format(
            datetime.now().date().strftime("%m-%d-%Y")
        ))


    def _create_request_dict_for_block(self, base_course, block, base_course_language):
        """
        Returns request dict required for update pages API of Wiki Meta
        {
            "title": "base_course_id/base_course_block_id/base_course_language",
            "@metadata": {
                "sourceLanguage": "fr",    //base_course_language
                "priorityLanguages": [],   //required_translation_languages
                "allowOnlyPriorityLanguages": true,
                "description": "Description for the component"
            },
            "block_id__display_name": "Problem display name",
            "block_id__content": "Problem html content"
        }
        """
        request = {}
        # title format is course_id/course_lang_code/block_id
        request["title"] = "{}/{}/{}".format(
            str(base_course), base_course_language, str(block.block_id)
        )
        request["@metadata"] = {
            "sourceLanguage": base_course_language,
            "priorityLanguages": json.loads(block.lang),
            "allowOnlyPriorityLanguages": True,
            "description": {
                "base_course_block": str(block.block_id),
                "base_course_block_type": json.dumps(
                    [data.data_type for data in block.courseblockdata_set.all()]
                )
            }
        }
        return request

    def _get_request_data_dict(self):
        """
        Returns dict of data required to fetch updated translations from Wiki Meta.
        Translations need to be fetched only if direction_flag of target block is destination.
        {
            "block-v1:edX+fresh1+fresh1+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b": {
                "source_course_id": "source_course_id_1",
                "source_course_lang_code": "en",
                "versions": {
                    fr: {
                        target_block_id: "block-v1:edX+fresh1+duplicate_str+type@chapterblock@a7e862b4a8b34c8f9c4870b44cbed97b",
                        target_course_id: "target_course_id_1"
                        data_types: [dislay_name, content]
                    },
                    hi: {
                        target_block_id: "block-v1:edX fresh1 hindi_ver2+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b",
                        target_course_id: "target_course_id_2"
                        data_types: [dislay_name, content]
                    }
                }
            }
            ...
        }

        """

        # Filter out all untranslated strings and check for latest updates for already translated strings.
        comparison_date = (datetime.now() - timedelta(days=3)).date()
        tranlsation_objects = WikiTranslation.objects.filter(
            Q(translation=None) | Q(last_fetched=None) | Q(last_fetched__date__gte=comparison_date)
        ).select_related(
            "target_block"
        ).select_related(
            "source_block_data",
            "source_block_data__course_block"
        )
        data_dict = {}
        for translation_obj in tranlsation_objects:
            source_block = translation_obj.source_block_data.course_block
            target_block = translation_obj.target_block
            source_block_key = str(source_block.block_id)
            if not target_block.is_source():
                target_language = get_course_by_id(target_block.course_id).language
                source_language = get_course_by_id(source_block.course_id).language
                if source_block_key in data_dict:
                    if target_language in data_dict[source_block_key]["versions"]:
                        target_obj = data_dict[source_block_key]["versions"].get(target_language)
                        existing_target_block_id = target_obj.get("target_block_id")
                        if existing_target_block_id and existing_target_block_id == str(target_block.block_id):
                            data_types_list = target_obj.get("data_types", [])
                            data_types_list.append(translation_obj.source_block_data.data_type)
                            target_obj["data_types"] = data_types_list
                        else:
                            raise Exception(
                                "Multiple target blocks found against single source block in target_language: {}".format(
                                    target_language
                                )
                            )
                    else:
                        target_obj = {
                            "target_block_id": str(target_block.block_id),
                            "target_course_id": str(target_block.course_id),
                            "data_types": [translation_obj.source_block_data.data_type]
                        }
                    data_dict[source_block_key]["versions"][target_language] = target_obj
                else:
                    data_dict[source_block_key] = {
                        "source_course_id": str(source_block.course_id),
                        "source_course_lang_code": source_language,
                        "versions": {
                            target_language: {
                                "target_block_id": str(target_block.block_id),
                                "target_course_id": str(target_block.course_id),
                                "data_types": [translation_obj.source_block_data.data_type]
                            }
                        }
                    }
        return data_dict

    def _get_tasks_to_fetch_data_from_wiki_meta(self, data_dict, meta_client, session):
        """
        Returns list of tasks - required for Async API calls of Meta Wiki to fetch translations.
        """
        tasks = []
        for source_block_key, source_block_mapping in data_dict.items():
            source_course_id = source_block_mapping.get("source_course_id")
            source_lang_code = source_block_mapping.get("source_course_lang_code")
            for target_lang_code, target_block_detail in source_block_mapping.get("versions", {}).items():
                mcgroup = "{}/{}/{}".format(source_course_id, source_lang_code, source_block_key)
                mclanguage = target_lang_code
                tasks.append(
                    meta_client.sync_translations(
                        mcgroup, mclanguage, session
                    )
                )
                break; #TODO: remove it
        return tasks

    async def async_fetch_data_from_wiki_meta(self, data_dict):
        """
        Async calls to fetch tramslations for course blocks.
        """
        responses = []
        async with aiohttp.ClientSession() as session:
            meta_client = WikiMetaClient()
            tasks = self._get_tasks_to_fetch_data_from_wiki_meta(data_dict, meta_client, session)
            responses = await asyncio.gather(*tasks)

    def handle(self, *args, **options):
        data_dict = self._get_request_data_dict()

        if options.get('commit'):
            if data_dict:
                asyncio.run(self.async_fetch_data_from_wiki_meta(data_dict))
            else:
                log.info("No updated course blocks data found to send on Meta Wiki.")

            # self._log_final_report()
        else:
            log.info(json.dumps(data_dict, indent=4))
