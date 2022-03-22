"""
Views for MetaTranslation v0 API(s)
"""
import json
from opaque_keys.edx.keys import CourseKey
from django.utils.translation import ugettext as _
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from cms.djangoapps.contentstore.outlines import get_outline_from_modulestore
from xmodule.modulestore.django import modulestore
from cms.djangoapps.contentstore.views.course import _course_outline_json
from opaque_keys.edx.keys import UsageKey
from common.lib.xmodule.xmodule.modulestore.django import modulestore
from xmodule.video_module.transcripts_utils import get_video_transcript_content


class GetTranslationOutlineStructure(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        course_id = kwargs.get('course_key_string')
        course_key = CourseKey.from_string(course_id)
        outline, _ = get_outline_from_modulestore(course_key)
        sections = []
        for section in outline.sections:
            section_data = {}
            section_data['title'] = section.title
            section_data['usage_key'] = str(section.usage_key)
            section_data['children'] = []
            for subsection in section.sequences:
                subsection_data = {}
                subsection_data['title'] = subsection.title
                subsection_data['usage_key'] = str(subsection.usage_key)
                section_data['children'].append(subsection_data)
            sections.append(section_data)
        return Response(json.dumps(sections), status=status.HTTP_200_OK)

class GetSubSectionContent(generics.RetrieveAPIView):
    
    def _get_video_subtitles(self, video_id, language):
        data = get_video_transcript_content(video_id, language)
        json_content = json.loads(data['content'].decode("utf-8"))
        return json_content['text']

    def get(self, request, *args, **kwargs):
        usage_key = kwargs.get('subsection_id')
        block_location = UsageKey.from_string(usage_key)
        units_children = modulestore().get_item(block_location).children
        units = []
        for unit_key in units_children:
            unit = modulestore().get_item(unit_key)
            unit_data = {}
            unit_data['display_name'] = unit.display_name
            unit_data['usage_key'] = str(unit_key)
            unit_data['children'] = []
            for component_key in unit.children:
                component = modulestore().get_item(component_key)
                component_data = {}
                component_data['display_name'] = component.display_name
                component_data['usage_key'] = str(component_key)
                component_data['category'] = component.category
                if component.category == 'video':
                    component_data['data'] =  self._get_video_subtitles(component.edx_video_id, component.transcript_language)
                else:
                    component_data['data'] = component.data
                unit_data['children'].append(component_data)
            units.append(unit_data)
        return Response(json.dumps(units), status=status.HTTP_200_OK)

        