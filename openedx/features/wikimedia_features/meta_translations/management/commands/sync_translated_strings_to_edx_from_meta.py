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

    _UPDATED_TRANSLATIONS = []
    _WIKI_TRANSLATIONS_OBJECTS = None


    def add_arguments(self, parser):
        """
        Add --commit argument with default value False
        """
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Send API calls to Meta wiki',
        )

    def _log_final_report(self, request_data_dict):
        """
        Log final results.
        """
        log.info('\n\n\n')
        log.info("--------------------- WIKI META FETCHED PAGES RESULT- {} ---------------------".format(
            datetime.now().date().strftime("%m-%d-%Y")
        ))
        log.info("Request data dict: {}".format(json.dumps(request_data_dict, indent=4)))
        log.info("Updated Translations: {}".format(json.dumps(self._UPDATED_TRANSLATIONS, indent=4)))

    def _get_request_data_dict(self):
        """
        Returns dict of data required to fetch updated translations from Wiki Meta.
        Translations need to be fetched only if direction_flag of target block is destination.

        i.e for source block => block-v1:edX+fresh1+fresh1+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b
        {
            "block-v1:edX+fresh1+fresh1+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b": {
                "source_course_id": "source_course_id_1",
                "source_course_lang_code": "en",
                "target_block_versions" : {
                    "fr": "block-v1:edX+fresh1+duplicate_str+type@chapterblock@a7e862b4a8b34c8f9c4870b44cbed97b",
                    "hi": "block-v1:edX fresh1 hindi_ver2+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b",
                }
            }
            ...
        }

        """
        # Filter out all untranslated strings and check for latest updates for already translated strings.
        comparison_date = (datetime.now() - timedelta(days=3)).date()
        tranlsation_objects = WikiTranslation.objects.filter(
            Q(translation=None) | Q(last_fetched=None) | Q(last_fetched__date__lte=comparison_date)
        ).select_related("target_block").select_related("source_block_data", "source_block_data__course_block")
        self._WIKI_TRANSLATIONS_OBJECTS = tranlsation_objects

        data_dict = {}
        for translation_obj in tranlsation_objects:
            source_block = translation_obj.source_block_data.course_block
            target_block = translation_obj.target_block
            source_block_key = str(source_block.block_id)
            if not target_block.is_source():
                target_language = get_course_by_id(target_block.course_id).language
                source_language = get_course_by_id(source_block.course_id).language
                if source_block_key in data_dict:
                    data_dict[source_block_key]["target_block_versions"][target_language] = str(target_block.block_id)
                else:
                    data_dict[source_block_key] = {
                        "source_course_id": str(source_block.course_id),
                        "source_course_lang_code": source_language,
                        "target_block_versions": {
                            target_language: str(target_block.block_id),
                        }
                    }
        return data_dict

    def _update_translations_in_db(self, translation_obj, updated_translation, updated_commits, source_block_data, target_lang_code):
        translation_obj.translation = updated_translation
        translation_obj.approved = False
        translation_obj.approved_by = None
        translation_obj.last_fetched = datetime.now()
        translation_obj.fetched_commits = updated_commits
        translation_obj.save()

        translation_obj.target_block.applied = False
        translation_obj.target_block.save()

        log.info("Translations have been updated for block_id: {}, data_type: {}, target_language: {}".format(
            str(translation_obj.target_block.block_id),
            source_block_data.data_type,
            target_lang_code
        ))
        self._UPDATED_TRANSLATIONS.append({
            "target_block_id": str(translation_obj.target_block.block_id),
            "source_block_data_type": source_block_data.data_type,
            "target_language_code": target_lang_code,
            "message": "Updated"
        })


    def _check_and_update_translations(self, response_data, wiki_translations, target_language_code):
        """
        Update WikiTranslations with fetched translated strings from meta-server

        Arguments:
            response_data (Dict): contains translations
            translations (WikiTranslation Queryset): Queryset that need to be updated
            target_language_code (String): target block language.

        Sample response_data:
        "display_name": {
            "key": "Course-v1:edX+fresh1+fresh1/en/block-v1:edX+fresh1+fresh1+type@problem+block@9eefa6c9923346b1b746988401c638ad/display_name",
            "translation": "चेक बॉक्",
            "properties": {
                "revision" : 1232323,
                "reviewers": [4876]
                "status": "translated",
                "last-translator-text": "wikimeta-translator-username",
                "last-translator-id": "wikimeta-translator-userid",
            },
            "title": "Translations:Course-v1:edX+fresh1+fresh1/en/block-v1:edX+fresh1+fresh1+type@problem+block@9eefa6c9923346b1b746988401c638ad/display_name/hi",
            "targetLanguage": "hi",
            "primaryGroup": "messagebundle-Course-v1:edX+fresh1+fresh1/en/block-v1:edX+fresh1+fresh1+type@problem+block@9eefa6c9923346b1b746988401c638ad",
        },
        ...
        """
        for translation_obj in wiki_translations:
            source_block_data = translation_obj.source_block_data
            if not translation_obj.translation or not translation_obj.last_fetched or not translation_obj.fetched_commits:
                # No need to compare commits, save translations and commits in DB directly
                fetched_commits = {}
                if source_block_data.parsed_keys:
                    translated_data = {}
                    for key, value in source_block_data.parsed_keys.items():
                        key_response = response_data.get(key, {})
                        if key_response.get('properties', {}).get('status') == "translated":
                            translated_data.update({key: key_response.get('translation')})
                            fetched_commits.update({key: key_response.get('properties', {}).get('revision')})
                    if translated_data:
                        translated_data = json.dumps(translated_data)
                        self._update_translations_in_db(translation_obj, translated_data, fetched_commits, source_block_data, target_language_code)
                    else:
                        self._UPDATED_TRANSLATIONS.append({
                            "target_block_id": str(translation_obj.target_block.block_id),
                            "source_block_data_type": source_block_data.data_type,
                            "target_language_code": target_language_code,
                            "message": "Successfully fetched but no key is translated"
                        })
                else:
                    key_response = response_data.get(source_block_data.data_type, {})
                    if key_response.get('properties', {}).get('status') == "translated":
                        translated_data = response_data.get(source_block_data.data_type, {}).get('translation')
                        fetched_commits.update({source_block_data.data_type: key_response.get('properties', {}).get('revision')})
                        self._update_translations_in_db(translation_obj, translated_data, fetched_commits, source_block_data, target_language_code)
                    else:
                        self._UPDATED_TRANSLATIONS.append({
                            "target_block_id": str(translation_obj.target_block.block_id),
                            "source_block_data_type": source_block_data.data_type,
                            "target_language_code": target_language_code,
                            "message": "Successfully fetched but status is not translated"
                        })
            else:
                # Compare commits of tranlsations with existing db commits -> only update translations if commits are updated.
                existing_translation = translation_obj.translation
                existing_commits = translation_obj.fetched_commits
                if source_block_data.parsed_keys:
                    is_any_key_updated = False
                    for key, value in source_block_data.parsed_keys.items():
                        key_response = response_data.get(key, {})
                        key_commit = key_response.get('properties', {}).get('revision')
                        if key_response.get('properties', {}).get('status') == "translated" and not existing_commits.get(key) or (key_commit and key_commit != existing_commits.get(key)):
                            existing_translation.update({key: key_response.get('translation')})
                            existing_commits.update({key: key_commit})
                            is_any_key_updated = True
                else:
                    is_any_key_updated = False
                    key_response = response_data.get(source_block_data.data_type, {})
                    key_commit = key_response.get('properties', {}).get('revision')
                    source_block_data.data_type
                    if key_response.get('properties', {}).get('status') == "translated" and not existing_commits.get(source_block_data.data_type) or (key_commit and key_commit != existing_commits.get(source_block_data.data_type)):
                        existing_translation = key_response.get('translation')
                        existing_commits.update({source_block_data.data_type: key_commit})
                        is_any_key_updated = True

                if is_any_key_updated:
                    self._update_translations_in_db(
                        translation_obj, existing_translation, existing_commits, source_block_data, target_language_code
                    )
                else:
                    translation_obj.last_fetched = datetime.now()
                    translation_obj.save()

                    self._UPDATED_TRANSLATIONS.append({
                        "target_block_id": str(translation_obj.target_block.block_id),
                        "source_block_data_type": source_block_data.data_type,
                        "target_language_code": target_language_code,
                        "message": "Successfully fetched but commits are same"
                    })


    def _update_response_translations_in_db(self, data_dict, responses):
        """
        Update WikiTranslations with fetched translated response from meta-server

        Arguments:
            data_dict (Dict): contains request data that used for Send API call
            responses (list): fetched responses list

        Sample data_dict:
        i.e for source block => block-v1:edX+fresh1+fresh1+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b
        {
            "block-v1:edX+fresh1+fresh1+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b": {
                "source_course_id": "source_course_id_1",
                "source_course_lang_code": "en",
                "target_block_versions" : {
                    "hi": "block-v1:edX fresh1 hindi_ver2+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b",
                }
            }
            ...
        }
        Sample responses:
        [
            {
                'response_source_block': "block-v1:edX+fresh1+fresh1+type@chapter+block@a7e862b4a8b34c8f9c4870b44cbed97b",
                'mclanguage': "hi",
                'response_data':  {
                    "display_name": {
                        "key": "Course-v1:edX+fresh1+fresh1/en/block-v1:edX+fresh1+fresh1+type@problem+block@9eefa6c9923346b1b746988401c638ad/display_name",
                        "translation": "चेक बॉक्",
                        "properties": {
                            "status": "translated",
                            "last-translator-text": "wikimeta-translator-username",
                            "last-translator-id": "wikimeta-translator-userid",
                        },
                        "title": "Translations:Course-v1:edX+fresh1+fresh1/en/block-v1:edX+fresh1+fresh1+type@problem+block@9eefa6c9923346b1b746988401c638ad/display_name/hi",
                        "targetLanguage": "hi",
                        "primaryGroup": "messagebundle-Course-v1:edX+fresh1+fresh1/en/block-v1:edX+fresh1+fresh1+type@problem+block@9eefa6c9923346b1b746988401c638ad",
                    }
                }
            }
        ]
        """
        if not self._WIKI_TRANSLATIONS_OBJECTS:
            comparison_date = (datetime.now() - timedelta(days=3)).date()
            self._WIKI_TRANSLATIONS_OBJECTS = WikiTranslation.objects.filter(
                Q(translation=None) | Q(last_fetched=None) | Q(last_fetched__date__lte=comparison_date)
            ).select_related("target_block").select_related("source_block_data")

        for response in responses:
            if not response:
                continue;

            response_source_block = response.get('response_source_block')
            target_language_code = response.get('mclanguage')
            response_data = response.get('response_data')
            target_block_id = data_dict.get(response_source_block, {}).get('target_block_versions', {}).get(
                target_language_code
            )

            if not response_source_block or not response_source_block or not response_source_block or not target_block_id:
                log.error("Error in updating translations in db due to invalid response or data_dict.")
                log.error(
                    "Response details => response_source_block: {}, target_language_code: {}, response_data: {}".format(
                        response_source_block, response_source_block, response_source_block
                    )
                )
                continue;

            translations = self._WIKI_TRANSLATIONS_OBJECTS.filter(target_block__block_id=target_block_id)
            self._check_and_update_translations(response_data, translations, target_language_code)

    def _get_tasks_to_fetch_data_from_wiki_meta(self, data_dict, meta_client, session):
        """
        Returns list of tasks - required for Async API calls of Meta Wiki to fetch translations.
        """
        tasks = []
        for source_block_key, source_block_mapping in data_dict.items():
            source_course_id = source_block_mapping.get("source_course_id")
            source_lang_code = source_block_mapping.get("source_course_lang_code")
            for target_lang_code in source_block_mapping.get("target_block_versions", {}).keys():
                mcgroup = "{}/{}/{}".format(source_course_id, source_lang_code, source_block_key)
                mclanguage = target_lang_code
                tasks.append(
                    meta_client.sync_translations(
                        mcgroup, mclanguage, session
                    )
                )
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
            self._update_response_translations_in_db(data_dict, responses)

    def handle(self, *args, **options):
        data_dict = self._get_request_data_dict()

        if options.get('commit'):
            if data_dict:
                asyncio.run(self.async_fetch_data_from_wiki_meta(data_dict))
            else:
                log.info("No Translations need to fetched/updated from Meta Wiki.")

            self._log_final_report(data_dict)
        else:
            log.info(json.dumps(data_dict, indent=4))
