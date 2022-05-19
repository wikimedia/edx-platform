import os
import json

from logging import getLogger
from abc import ABC, abstractmethod
from webob import Request
from django.conf import settings

from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation, WikiTranslation
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
        return {
            "display_name": block.display_name,
            "content": block.data
        }

class ProblemComponent(WikiComponent):
    """
    Handle Problem type blocks i.e checkbox, multiple choice etc
    """
    def __init__(self, mapping=False):
        self.mapping = mapping
        super().__init__()
    
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
            block_id = block.scope_ids.usage_id
            translation = WikiTranslation.objects.get(target_block__block_id=block_id, source_block_data__data_type='content')
            source_xml_data = translation.source_block_data.data
            meta_data = {
                'xml_data': source_xml_data,
                'encodings': json.loads(data['content'])
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
        return {
            "display_name": block.display_name,
            "content": block.data
        }

class VideoComponent(WikiComponent):
    """
    Handle Video type blocks i.e video
    Parameters:
        mapping (bool): To change content of get function based on course type 
                        (base_course, translated_course)
    Use of mapping:
        On calling video-component with mapping=False. It returns "video-transcripts"
        in a course language. On a translated course, it retures empty transcript, because 
        there is no transcript available in new langauge selected at time of translated return.
        Mapping = False solves this problem. It fetchs the language of a base course and
        returns translation in a base course language.
        
        More Explanation:
        At time of creating rerun, in video component all the transcripts are copied from
        base course to translated course. If we have English Transcript in a English course
        that it's also copied in (Spanish translated course). So there is a English transcript
        in video component of Spanish Course but no Spanish translation. We can then request
        Wiki Meta Server to translate English translation to Spanish One (By click Mapping button).
        When we get Spanish Translation from a Wiki Server. We will add a Spanish translations
        in translated Spanish course only.
    """
    def __init__(self, mapping=False):
        self.mapping = mapping
        super().__init__()

    def _get_base_course_language(self, course_id):
        """
        Returns langauge of a base course
        """
        try:
            course_translation = CourseTranslation.objects.get(course_id=course_id)
            base_course = get_course_by_id(course_translation.base_course_id)
            return base_course.language
        except CourseTranslation.DoesNotExist:
            log.error("Course {} is not a translated course".format(course_id))
    
    def _get_valid_language(self, course_id):
        """
        Returns a valid langauge based on value of mapping
        """
        if not self.mapping:
            course = get_course_by_id(course_id)
            return course.language
        return self._get_base_course_language(course_id)
    
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
            base_course_langauge = self._get_base_course_language(block.course_id)
            if base_course_langauge:
                video_data = get_video_transcript_content(block.edx_video_id, base_course_langauge)
                if video_data:
                    json_content = self._get_json_transcript_data(video_data['file_name'], video_data['content'])
                    json_content['text'] = json.loads(data['transcript'])

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
                else:
                    log.error('No Transcript found for languge code {}'.format(base_course_langauge))
        
        return modulestore().update_item(block, 'edx')
    
    def get(self, block):
        """    
        Arguments:
            block: module type course-outline block

        Returns:
            dict of extracted data
        """
        language = self._get_valid_language(block.course_id)
        data = get_video_transcript_content(block.edx_video_id, language)
        video_context = { "display_name": block.display_name}
        if data:
            json_content = self._get_json_transcript_data(data['file_name'], data['content'])
            video_context['transcript'] = json.dumps(json_content['text'])
        return video_context

COMPONENTS_CLASS_MAPPING = {
    'course': ModuleComponent,
    'chapter': ModuleComponent,
    'sequential': ModuleComponent,
    'vertical': ModuleComponent,
    'html': HtmlComponent,
    'problem': ProblemComponent,
    'video': VideoComponent
}
