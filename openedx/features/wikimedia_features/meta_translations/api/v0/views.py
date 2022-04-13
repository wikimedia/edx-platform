"""
Views for MetaTranslation v0 API(s)
"""

from rest_framework import generics
from rest_framework import status
from rest_framework import permissions
from rest_framework.response import Response
from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import UsageKey, CourseKey
from django.utils.translation import ugettext as _

from cms.djangoapps.contentstore.views.course import get_courses_accessible_to_user
from common.lib.xmodule.xmodule.modulestore.django import modulestore
from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.api.v0.utils import (
    get_courses_of_base_course, get_outline_course_to_units, get_outline_unit_to_components
    )
from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation

class GetTranslationOutlineStructure(generics.RetrieveAPIView):
    """
    API to get course outline of a course and it's base course
    Response:
        {
            "course_outline": {
                "7VLKTTPX1ZUJI8KA":{
                    "usage_key":"block_component_usage_id",
                    "category":"vertical",
                    "data_block_ids: {
                        "display_name": 1,
                    },
                    "data":{
                        "display_name":"Problem 1",
                    }
                    children: {
                        "8KLKTTPX1ZUJI8KA": {
                            "usage_key":"block_component_usage_id",
                            "category":"vertical",
                            "data_block_ids: {
                                "display_name": 2,
                            },
                            "data": {
                                "display_name": "Section 1" 
                            }
                            children: {
                                "9LLKTTPX1ZUJI8KA" {
                                    "usage_key":"block_component_usage_id",
                                    "category":"horizontal",
                                    "data_block_ids: {
                                        "display_name": 2,
                                    },
                                    "data: {
                                        "display_name": "Unit 1",
                                    },
                                }
                            }
                        }
                    }
                }
            },
            "base_course_outline": {
                "7VLKTTPX1ZUJI8KA":{
                    "usage_key":"base_block_component_usage_id",
                    "category":"vertical",
                    "data":{
                        "display_name":"Problem 1",
                    }
                    children: {
                        "8KLKTTPX1ZUJI8KA": {
                            "usage_key":"base_block_component_usage_id",
                            "category":"vertical",
                            "data": {
                                "display_name": "Section 1" 
                            }
                            children: {
                                "9LLKTTPX1ZUJI8KA" {
                                    "usage_key":"base_block_component_usage_id",
                                    "category":"horizontal",
                                    "data: {
                                        "display_name": "Unit 1",
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    permission_classes = (permissions.IsAuthenticated,)

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

        return Response(data, status=status.HTTP_200_OK)

class GetVerticalComponentContent(generics.RetrieveAPIView):
    """
    API to get component data of a course and it's base course
      Response:
        {
            'course_outline': {
                "7VLKTTPX1ZUJI8KA":{
                    "usage_key":"block_component_usage_id",
                    "category":"problem",
                    "data_block_ids: {
                        "display_name": 1,
                        "content": 10
                    },
                    "data":{
                        "display_name":"Problem 1",
                        "content":""
                    }
                },
                "B36BXKA90A56Y5QI":{
                    "usage_key":"block_component_usage_id",
                    "category":"html",
                    "data_block_ids: {
                        "display_name": 1,
                        "content": 10
                    },
                    "data": {
                        "display_name":"Html Text",
                        "content":"<h1>Hello World<h1/>"
                    }
                },
            }
            'base_course_outline': {
                "7VLKTTPX1ZUJI8KA":{
                    "usage_key":"base_block_component_usage_id",
                    "category":"problem",
                    "data":{
                        "display_name":"",
                        "content":""
                    }
                },
                "B36BXKA90A56Y5QI":{
                    "usage_key":"base_block_component_usage_id",
                    "category":"html",
                    "data": {
                        "display_name":"",
                        "content":""
                    }
                },
            } 
        }
    """
    permission_classes = (permissions.IsAuthenticated,)

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

        return Response(data, status=status.HTTP_200_OK)

class GetCoursesVersionInfo(generics.RetrieveAPIView):
    """
    API to get ids of user courses with their translated versions
    Response:
    {
        {
            "course_key_1" : {
                "id": "course_key_1",
                "title": "Introduction To Computing",
                "language": "en",
                "rerun": {
                    course_key_2: {
                        "id": "course_key_2",
                        "tilte": "Introduction To Computing(Urdu)",
                        "language": "ur",
                    },
                    course_key_2: {
                        "id": "course_key_3",
                        "tilte": "Introduction To Computing(French)",
                        "language": "fr",
                    }
                }
            }
        }
    }
    """
    permission_classes = (permissions.IsAuthenticated,)
    
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
        return Response(json_data, status=status.HTTP_200_OK)
