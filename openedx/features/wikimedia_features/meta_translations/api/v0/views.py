"""
Views for MetaTranslation v0 API(s)
"""
import json
from lms.djangoapps.courseware.courses import get_course_by_id
from opaque_keys.edx.keys import CourseKey
from django.utils.translation import ugettext as _
from openedx.features.wikimedia_features.meta_translations.api.v0.utils import get_courses_of_base_course, get_outline_course_to_units, get_outline_unit_to_components
from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from xmodule.modulestore.django import modulestore
from cms.djangoapps.contentstore.views.course import get_courses_accessible_to_user
from opaque_keys.edx.keys import UsageKey
from common.lib.xmodule.xmodule.modulestore.django import modulestore

class GetTranslationOutlineStructure(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        course_id = kwargs.get('course_key')
        course_key = CourseKey.from_string(course_id)
        course = get_course_by_id(course_key)

        course_outline, base_course_outline = get_outline_course_to_units(course)

        key, base_key = list(course_outline.keys())[0], list(base_course_outline.keys())[0]
        data = {
            'course_outline': course_outline[key]['children'],
            'base_course_outline': base_course_outline[base_key]['children']
        }

        return Response(json.dumps(data), status=status.HTTP_200_OK)

class GetVerticalComponentContent(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        usage_key = kwargs.get('unit_key')
        block_location = UsageKey.from_string(usage_key)

        unit = modulestore().get_item(block_location)

        unit_data, base_unit_data, = get_outline_unit_to_components(unit)
        key, base_key = list(unit_data.keys())[0], list(base_unit_data.keys())[0]

        data = {
            'components_data': unit_data[key]['children'],
            'base_components_data': base_unit_data[base_key]['children'],
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
