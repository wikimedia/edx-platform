"""
Views for MetaTranslation v0 API(s)
"""
import json
from lms.djangoapps.courseware.courses import get_course_by_id
from opaque_keys.edx.keys import CourseKey
from django.utils.translation import ugettext as _
from openedx.features.wikimedia_features.meta_translations.api.v0.utils import get_courses_of_base_course, get_outline_course_to_sections_testing, get_outline_subsections_to_component_testing
from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from xmodule.modulestore.django import modulestore
from cms.djangoapps.contentstore.views.course import get_courses_accessible_to_user
from opaque_keys.edx.keys import UsageKey
from common.lib.xmodule.xmodule.modulestore.django import modulestore
from xmodule.video_module.transcripts_utils import get_video_transcript_content


class GetTranslationOutlineStructure(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        course_id = kwargs.get('course_key')
        base_course_id = kwargs.get('base_course_key')

        course_key = CourseKey.from_string(course_id)
        base_course_key = CourseKey.from_string(base_course_id)

        course = get_course_by_id(course_key)
        base_course = get_course_by_id(base_course_key)

        base_course_outline, course_outline = get_outline_course_to_sections_testing(base_course, course)

        data = {
            'course_lang': course.language,
            'base_course_lang': base_course.language,
            'course_outline': course_outline,
            'base_course_outline': base_course_outline
        }

        return Response(json.dumps(data), status=status.HTTP_200_OK)

class GetSubSectionContent(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        usage_key = kwargs.get('subsection_key')
        base_usage_key = kwargs.get('base_subsection_key')

        block_location = UsageKey.from_string(usage_key)
        base_block_location = UsageKey.from_string(base_usage_key)

        subsection = modulestore().get_item(block_location)
        base_subsection = modulestore().get_item(base_block_location)

        base_units_data, units_data = get_outline_subsections_to_component_testing(base_subsection, subsection)

        data = {
            'units_data': units_data,
            'base_units_data': base_units_data,
        }

        return Response(json.dumps(data), status=status.HTTP_200_OK)

class GetCoursesVersionInfo(generics.RetrieveAPIView):
    def _course_version_format(self, course_key):
        course = get_course_by_id(course_key)
        base_course_obj = {
            'id': str(course.id),
            'title': str(course.display_name),
            'language': course.language,
            'rerun': get_courses_of_base_course(course.id)
        }
        return str(course.id), base_course_obj


    def get(self, request, *args, **kwargs):
        user_courses, _ = get_courses_accessible_to_user(request)
        course_keys = [course.id for course in user_courses]
        translated_courses = CourseTranslation.objects.filter(base_course_id__in=course_keys)
        base_course_keys = [translated_course.base_course_id for translated_course in translated_courses]
        base_course_keys = list(set(base_course_keys))
        data = [self._course_version_format(key) for key in base_course_keys]
        json_data = dict(data)
        return Response(json.dumps(json_data), status=status.HTTP_200_OK)
        
