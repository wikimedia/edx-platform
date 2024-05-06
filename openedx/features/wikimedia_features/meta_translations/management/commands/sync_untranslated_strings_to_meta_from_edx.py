"""
Django admin command to send untranslated data to Meta Wiki.
"""
import os
import asyncio
import aiohttp
import time
import json
from datetime import datetime
from logging import getLogger

from django.core.management.base import BaseCommand
from django.db.models import Q
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import (
    CourseTranslation, CourseBlock, CourseBlockData, MetaCronJobInfo
)
from openedx.features.wikimedia_features.meta_translations.meta_client import WikiMetaClient
from openedx.features.wikimedia_features.meta_translations.utils import get_course_description_by_id, get_studio_component_name

log = getLogger(__name__)
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


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
        parser.add_argument(
            '-bck',
            '--base-course-key',
            help='Specify course key',
            default=None,
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

    def _create_request_dict_for_block(self, base_course, block, block_data, base_course_language, base_course_name, base_course_description):
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
        description = '{} in {} - {}'.format(
            block.block_type, base_course_name, base_course_description
        )
        
        label = "{} - {}: {}".format(
            base_course_name, get_studio_component_name(block.block_type), block_data.filter(data_type="display_name")[0].data
        )

        request["@metadata"] = {
            "sourceLanguage": base_course_language,
            "priorityLanguages": json.loads(block.lang),
            "allowOnlyPriorityLanguages": True,
            "description": description,
            "label": label
        }
        return request

    def _get_request_data_list(self, master_courses=[]):
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
        if not master_courses: 
            master_courses = CourseTranslation.get_base_courses_list(outdated=True)
        
        data_list = []
        for base_course in master_courses:
            outdated_translation = CourseTranslation.is_outdated_course(base_course)
            base_course_language = None
            base_course_name = None
            base_course_description = None
            if outdated_translation:
                base_course_language = outdated_translation.extra['base_course_language']
                base_course_name = outdated_translation.extra.get('base_course_name', '')
                base_course_description = outdated_translation.extra.get('base_course_description', '')
            else:
                base_course_language = get_course_by_id(base_course).language
                base_course_name = get_course_by_id(base_course).display_name
                base_course_description = get_course_description_by_id(base_course)
            base_course_blocks = CourseBlock.objects.prefetch_related("courseblockdata_set").filter(
                course_id=base_course
            )
            for block in base_course_blocks:
                block_data = block.courseblockdata_set.all()
                if block_data.filter(Q(content_updated=True) | Q(mapping_updated=True)).exists():
                    request_arguments = self._create_request_dict_for_block(
                        base_course, block, block_data, base_course_language, base_course_name, base_course_description
                    )
                    for data in block_data:
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

    async def _request_meta_tasks_in_sequential_with_delay(self, tasks, delay_in_sec=20):
        """
        Returns list of responses - call each task with some delay
        """
        responses = []
        for index in range(len(tasks)):
            start_time = time.time()
            response = await tasks[index]
            end_time = time.time()
            execution_time = end_time - start_time
            responses.append(response)
            if  index != len(tasks)-1:
                delay = delay_in_sec - execution_time
                if delay > 0:
                    log.info(f'Waiting for a next request -> sleep({round(delay,2)})')
                    time.sleep(delay)
        return responses

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

                response_title =  response.get("title", "")
                response_title_prefix = response.get("title_prefix", "")
                log.info("Processing success response with title: {}".format(response_title))
                title = response_title.split("/")
                if len(title) >= 3:
                    try:
                        block_id = UsageKey.from_string(title[2])
                    except InvalidKeyError:
                        block_id = UsageKey.from_string(title[2].replace(" ", "_"))

                    course_block_data_items = CourseBlockData.objects.filter(course_block__block_id=block_id)
                    if course_block_data_items.exists():
                        course_block_data_items.update(
                            content_updated=False, mapping_updated=False
                        )
                        log.info("{} block data items for block: {} flags have been reset.".format(
                            len(course_block_data_items), block_id,
                        ))
                        success_responses_count += 1
                        try:
                            source_block = course_block_data_items.first().course_block
                            extra_json = source_block.extra
                            extra_json.update({
                                "meta_page_title": '{}{}'.format(response_title_prefix, response_title),
                            })
                            source_block.extra = extra_json
                            source_block.save()
                        except Exception as ex:
                            log.error("Unable to set base URL for block: {} and title: {}.".format(block_id, response_title))
                            log.error(ex)
                else:
                    log.error("Unable to extract updated block_id from Meta success response for title: {}.".format(response_title))

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
            responses = await self._request_meta_tasks_in_sequential_with_delay(
                tasks,
                delay_in_sec=meta_client._API_REQUEST_DELAY,
            )
            self._reset_mapping_updated_and_content_updated(responses)

    def update_info(self):
        """
        Adds entry to MetaCronJobInfo
        """
        try:
            latest_info = MetaCronJobInfo.objects.latest('change_date')
            MetaCronJobInfo.objects.create(sent_date = datetime.now(), fetched_date = latest_info.fetched_date)
        except MetaCronJobInfo.DoesNotExist:
            MetaCronJobInfo.objects.create(sent_date = datetime.now())
    
    def handle(self, *args, **options):
        """
        Send translations to the Meta Server
        """
        base_courses = []
        if options.get('base-course-key'):
            base_courses = [CourseKey.from_string(base_courses)]
        
        data_list = self._get_request_data_list(base_courses)
        if options.get('commit'):
            self._RESULT.update({"updated_blocks_count": len(data_list)})

            if data_list:
                asyncio.run(self.async_update_data_on_wiki_meta(data_list))
            else:
                log.info("No updated course blocks data found to send on Meta Wiki.")

            self.update_info()
            self._log_final_report()
        else:
            log.info(json.dumps(data_list, indent=4))
