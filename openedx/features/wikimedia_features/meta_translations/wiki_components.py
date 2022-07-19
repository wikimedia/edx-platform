import os
import json

from lxml import etree
from logging import getLogger
from abc import ABC, abstractmethod
from webob import Request
from django.conf import settings

from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation, WikiTranslation, CourseBlockData
from common.lib.xmodule.xmodule.video_module.transcripts_utils import (
        Transcript, convert_video_transcript, get_video_transcript_content
    )
from common.lib.xmodule.xmodule.modulestore.django import modulestore
from lms.djangoapps.courseware.courses import get_course_by_id

log = getLogger(__name__)

class WikiComponent(ABC):
    """
    Abstract class with update and get functions
    """
    @abstractmethod
    def update(self, block, data):
        """
        Abstract method update. Required in all children
        """
        pass

    @abstractmethod
    def get(self, block):
        """
        Abstract method get. Required in all children
        """
        pass

    @abstractmethod
    def check_and_sync_base_block_data(self, xblock, updated_xblock_data):
        """
        Abstract method get. Required in all children
        """
        pass

class ModuleComponent(WikiComponent):
    """
    Handle Module type blocks i.e sections, subsection and units
    """
    def update(self, block , data):
        """
        Update display_name of an xblock
        Arguments:
            block: module type course-outline block
            data: dict of extracted data

        Returns:
            block: module type course-outline block (updated block)
        """
        if 'display_name' in data:
            block.display_name = data['display_name']
        return modulestore().update_item(block, 'edx')

    def get(self, block):
        """
        Get display_name of an xblock
        Arguments:
            block: module type course-outline block

        Returns:
            dict of extracted data
        """
        return {
            'display_name': block.display_name
        }

    def check_and_sync_base_block_data(self, xblock, updated_xblock_data):
        """
        if base_block display_name is updated then
        - Sync updated data in db i.e CourseBlockData.
        - Set content_update to True so that next meta server send call would send updated content.
        - Reset all versions and translations.
        """
        display_name = updated_xblock_data.get('metadata', {}).get('display_name')
        if display_name and display_name != xblock.display_name:
            block_id = str(xblock.scope_ids.usage_id)
            CourseBlockData.update_base_block_data(block_id, "display_name", display_name)


class HtmlComponent(WikiComponent):
    """
    Handle HTML type blocks i.e problem and raw_html
    """
    def update(self, block , data):
        """
        Update display_name and data of an xblock
        Arguments:
            block: module type course-outline block
            data: dict of extracted data

        Returns:
            block: module type course-outline block (updated block)
        """
        if 'display_name' in data:
            block.display_name = data['display_name']
        if 'content' in data:
            block.data = data['content']
        return modulestore().update_item(block, 'edx')

    def get(self, block):
        """
        Arguments:
            block: module type course-outline block

        Returns:
            dict of extracted data
        """
        data = {'display_name': block.display_name}
        if block.data:
            data['content'] = block.data
        return data

    def check_and_sync_base_block_data(self, xblock, updated_xblock_data):
        """
        if base_block display_name or html content is updated then
        - Sync updated data in db i.e CourseBlockData.
        - Set content_update to True so that next meta server send call would send updated content.
        - Reset all versions and translations.
        """
        updated_display_name = updated_xblock_data.get('metadata', {}).get('display_name') or updated_xblock_data.get('display_name')
        if updated_display_name and updated_display_name != xblock.display_name:
            block_id = str(xblock.scope_ids.usage_id)
            CourseBlockData.update_base_block_data(block_id, "display_name", updated_display_name)

        updated_xml_content = updated_xblock_data.get('data')
        if updated_xml_content and updated_xml_content != xblock.data:
            block_id = str(xblock.scope_ids.usage_id)
            CourseBlockData.update_base_block_data(block_id, "content", updated_xml_content)

class ProblemComponent(WikiComponent):
    """
    Handle Problem type blocks i.e checkbox, multiple choice etc
    """
    def update(self, block , data):
        """
        Update display_name and data of an xblock
        Arguments:
            block: module type course-outline block
            data: dict of extracted data (content in data should be in key, value form)

        Returns:
            block: module type course-outline block (updated block)
        """

        if 'display_name' in data:
            block.display_name = data['display_name']
        if 'content' in data:
            block_id = block.scope_ids.usage_id
            translation = WikiTranslation.objects.get(target_block__block_id=block_id, source_block_data__data_type='content')
            source_xml_data = translation.source_block_data.data
            meta_data = {
                'xml_data': source_xml_data,
                'encodings': data['content']
            }
            updated_xml = settings.TRANSFORMER_CLASS_MAPPING[block.category]().meta_data_to_raw_data(meta_data)
            block.data = updated_xml

        return modulestore().update_item(block, 'edx')

    def get(self, block):
        """
        Arguments:
            block: module type course-outline block

        Returns:
            dict of extracted data
        """
        data = {'display_name': block.display_name}
        if block.data:
            parser = etree.XMLParser(remove_blank_text=True)
            problem = etree.XML(block.data, parser=parser)
            if problem.getchildren():
                data['content'] = block.data

        return data

    def check_and_sync_base_block_data(self, xblock, updated_xblock_data):
        """
        if base_block display_name or problem xml content is updated then
        - Sync updated data in db i.e CourseBlockData.
        - Set content_update to True so that next meta server send call would send updated content.
        - Reset all versions and translations.
        """
        updated_display_name = updated_xblock_data.get('metadata', {}).get('display_name') or updated_xblock_data.get('display_name')
        if updated_display_name and updated_display_name != xblock.display_name:
            block_id = str(xblock.scope_ids.usage_id)
            CourseBlockData.update_base_block_data(block_id, "display_name", updated_display_name)

        updated_xml_content = updated_xblock_data.get('data')
        if updated_xml_content and updated_xml_content != xblock.data:
            block_id = str(xblock.scope_ids.usage_id)
            CourseBlockData.update_base_block_data(block_id, "content", updated_xml_content)

class VideoComponent(WikiComponent):
    """
    Handle Video type blocks i.e video
    """
    def _get_base_course_language(self, course_id):
        """
        Returns langauge of a base course
        """
        try:
            course_translation = CourseTranslation.objects.get(course_id=course_id)
            base_course = get_course_by_id(course_translation.base_course_id)
            return base_course.language
        except CourseTranslation.DoesNotExist:
            if CourseTranslation.objects.filter(base_course_id=course_id).exists():
                base_course = get_course_by_id(course_id)
                return base_course.language
            else:
                log.error("Unable to get base course language for video component.")
                log.error("Course {} is neither a translated course nor base course".format(course_id))

    def _get_json_transcript_data(self, file_name, content):
        """
        Return dict of subtitiles from content
        """
        if os.path.splitext(file_name) != Transcript.SJSON:
            content = convert_video_transcript(file_name, content, Transcript.SJSON)['content']
        if isinstance(content, str):
            return json.loads(content)
        return json.loads(content.decode("utf-8"))

    def update(self, block , data):
        """
        Update display_name and transcript of an xblock
        Arguments:
            block: module type course-outline block
            data: dict of extracted data

        Returns:
            block: module type course-outline block (updated block)
        """
        if 'display_name' in data:
            block.display_name = data['display_name']
        if 'transcript' in data:
            course = get_course_by_id(block.course_id)
            block_id = block.scope_ids.usage_id
            translation = WikiTranslation.objects.get(target_block__block_id=block_id, source_block_data__data_type='transcript')
            json_content = json.loads(translation.source_block_data.data)

            meta_data = {
                'start_points': json_content['start'],
                'end_points': json_content['end'],
                'encodings': data['transcript']
            }
            updated_transcript = settings.TRANSFORMER_CLASS_MAPPING[block.category]().meta_data_to_raw_data(meta_data)
            json_content['text'] = updated_transcript

            sjson_content = json.dumps(json_content).encode('utf-8')
            SRT_content = Transcript.convert(sjson_content, Transcript.SJSON, Transcript.SRT)

            language_code = course.language
            post_data = {
                        "edx_video_id": block.edx_video_id,
                        "language_code": language_code,
                        "new_language_code": language_code,
                        "file": ('translation-{}.srt'.format(language_code), SRT_content)
                    }

            request = Request.blank('/translation', POST=post_data)
            block.studio_transcript(request=request, dispatch="translation")

        return modulestore().update_item(block, 'edx')

    def get(self, block):
        """
        Arguments:
            block: module type course-outline block

        Returns:
            dict of extracted data
        """
        language = self._get_base_course_language(block.course_id)
        data = get_video_transcript_content(block.edx_video_id, language)
        video_context = { "display_name": block.display_name}
        if data:
            json_content = self._get_json_transcript_data(data['file_name'], data['content'])
            video_context['transcript'] = json.dumps(json_content)
        return video_context

    def check_and_sync_base_block_data(self, xblock, updated_xblock_data):
        """
        if base_block display_name or video transcript is updated then
        - Sync updated data in db i.e CourseBlockData.
        - Set content_update to True so that next meta server send call would send updated content.
        - Reset all versions and translations.
        """
        block_id = str(xblock.scope_ids.usage_id)

        updated_display_name = updated_xblock_data.get('metadata', {}).get('display_name') or updated_xblock_data.get('display_name')
        if updated_display_name and updated_display_name != xblock.display_name:
            CourseBlockData.update_base_block_data(block_id, "display_name", updated_display_name)

        # For transcript we do not get data in json so we'll compare transcript uploaded in xblock and transcript content
        # saved in meta_translations db i.e CourseBlockData
        current_video_data = self.get(xblock)
        current_video_transcript = current_video_data.get("transcript")
        if current_video_transcript:
            try:
                course_block_data = CourseBlockData.objects.get(course_block__block_id=block_id, data_type="transcript")
                if current_video_transcript != course_block_data.data:
                    CourseBlockData.update_base_block_data(block_id, "transcript", current_video_transcript, course_block_data)
            except CourseBlockData.DoesNotExist:
                pass

COMPONENTS_CLASS_MAPPING = {
    'course': ModuleComponent,
    'chapter': ModuleComponent,
    'sequential': ModuleComponent,
    'vertical': ModuleComponent,
    'html': HtmlComponent,
    'problem': ProblemComponent,
    'video': VideoComponent
}
