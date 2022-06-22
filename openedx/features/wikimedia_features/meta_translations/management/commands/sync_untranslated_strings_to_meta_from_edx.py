"""
Django admin command to send untranslated data to Meta Wiki.
"""
import asyncio
import aiohttp
import json
from datetime import datetime
from logging import getLogger

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import (
    WikiTranslation, CourseTranslation, CourseBlock, CourseBlockData
)
from openedx.features.wikimedia_features.meta_translations.meta_client import WikiMetaClient

log = getLogger(__name__)


class Command(BaseCommand):
    """
    This command will check and send updated block strings to meta server for translations.

        $ ./manage.py cms sync_untranslated_strings_to_meta_from_edx
        It will show all updated blocks that are ready to send.

        $ ./manage.py cms sync_untranslated_strings_to_meta_from_edx --commit
        It will send API calls of Wiki Meta to update message groups.
    """
    help = 'Command to send untranslated strings to Meta server for translation'
    _RESULT = {
        "updated_blocks_count": 0,
        "success_updated_pages_count": 0
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
        log.info('Total number of updated blocks: {}'.format(self._RESULT.get("updated_blocks_count")))
        log.info('Total blocks updated successfully: {}'.format(self._RESULT.get("success_updated_pages_count")))

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
        }
        return request

    def _get_request_data_list(self):
        """
        Returns list of request dict required for update pages API of Wiki Meta for all updated blocks.
        Blocks need to be updated on Meta => if block-data content is updated or block-data mapping is updated.
        [
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
            },
            ...
        ]
        """
        master_courses = CourseTranslation.get_base_courses_list()
        data_list = []
        for base_course in master_courses:
            base_course_language = get_course_by_id(base_course).language
            base_course_blocks = CourseBlock.objects.prefetch_related("courseblockdata_set").filter(
                course_id=base_course
            )
            for block in base_course_blocks:
                if block.block_type != 'course':
                    updated_block_data = block.courseblockdata_set.filter(
                        Q(content_updated=True) | Q(mapping_updated=True)
                    )
                    if updated_block_data.exists():
                        request_arguments = self._create_request_dict_for_block(base_course, block, base_course_language)
                        for data in updated_block_data:
                            if data.parsed_keys:
                                request_arguments.update(data.parsed_keys)
                            else:
                                request_arguments.update({
                                    data.data_type: data.data
                                })
                        data_list.append(request_arguments)
        return data_list

    def _get_tasks_to_updated_data_on_wiki_meta(self, data_list, meta_client, session, csrf_token):
        """
        Returns list of tasks - required for Async API calls of Meta Wiki to update message group pages.
        """
        tasks = []
        for component in data_list:
            title = component.pop('title')
            tasks.append(
                meta_client.create_update_message_group(
                    title,
                    component,
                    session,
                    csrf_token,
                )
            )
        return tasks

    def _reset_mapping_updated_and_content_updated(self, responses):
        """
        Reset mapping_updated and content_updated for all the blocks-data that have been successfully sent
        on Wiki Meta. It will save unnecessary API calls as next time cron job will only send data for which either
        content_updated (base course content is updated) or
        mapping_updated (either direction_flag is updated or block mapping is updated i.e new lang re-run block added/deleted)
        """
        success_responses_count = 0
        for response in responses:
            if response and response.get("result", "").lower() == "success":
                # title format is course_id/course_lang_code/block_id
                title =  response.get("title", "").split("/")
                if len(title) >= 3:
                    try:
                        block_id = UsageKey.from_string(title[2])
                    except InvalidKeyError:
                        block_id = UsageKey.from_string(title[2].replace(" ", "_"))

                    CourseBlockData.objects.filter(course_block__block_id=block_id).update(
                        content_updated=False, mapping_updated=False
                    )
                    success_responses_count += 1
                else:
                    log.error("Unable to extract updated block_id from Meta success response.")

                self._RESULT.update({
                     "success_updated_pages_count": success_responses_count
                })

    async def async_update_data_on_wiki_meta(self, data_list):
        """
        Async calls to create/update pages for updated blocks data.
        """
        responses = []
        async with aiohttp.ClientSession() as session:
            meta_client = WikiMetaClient()
            await meta_client.login_request(session)
            csrf_token = await meta_client.fetch_csrf_token(session)
            tasks = self._get_tasks_to_updated_data_on_wiki_meta(data_list, meta_client, session, csrf_token)
            responses = await asyncio.gather(*tasks)
            self._reset_mapping_updated_and_content_updated(responses)

    def handle(self, *args, **options):
        data_list = self._get_request_data_list()
        if options.get('commit'):
            self._RESULT.update({"updated_blocks_count": len(data_list)})

            if data_list:
                asyncio.run(self.async_update_data_on_wiki_meta(data_list))
            else:
                log.info("No updated course blocks data found to send on Meta Wiki.")

            self._log_final_report()
        else:
            log.info(json.dumps(data_list, indent=4))
