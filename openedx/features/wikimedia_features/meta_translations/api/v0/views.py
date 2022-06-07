"""
Views for MetaTranslation v0 API(s)
"""


from rest_framework import generics
from rest_framework import status
from rest_framework import permissions
from rest_framework import viewsets
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
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock, CourseTranslation, WikiTranslation
from openedx.features.wikimedia_features.meta_translations.api.v0.serializers import CourseBlockSerializer, WikiTranslationSerializer
from openedx.features.wikimedia_features.meta_translations.api.v0.permissions import DestinationCourseOnly
from common.djangoapps.student.roles import CourseStaffRole

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
                    "status": {
                        "applied": false,
                        "approved": false,
                        "last_fetched": null,
                        "approved_by": edx
                    },
                    children: {
                        "8KLKTTPX1ZUJI8KA": {
                            "usage_key":"block_component_usage_id",
                            "category":"vertical",
                            "data_block_ids: {
                                "display_name": 2,
                            },
                            "status": {
                                "applied": false,
                                "approved": false,
                                "last_fetched": null,
                                "approved_by": edx
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

        if course_outline and base_course_outline:
            key, base_key = list(course_outline.keys())[0], list(base_course_outline.keys())[0]
            course_outline, base_course_outline = course_outline[key]['children'], base_course_outline[base_key]['children']

        data = {
            'course_outline': course_outline,
            'base_course_outline': base_course_outline,
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
                    "status": {
                        "applied": false,
                        "approved": false,
                        "last_fetched": null,
                        "approved_by": edx
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
                    "status": {
                        "applied": false,
                        "approved": false,
                        "last_fetched": null,
                        "approved_by": edx
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
        if unit_data and base_unit_data:
            key, base_key = list(unit_data.keys())[0], list(base_unit_data.keys())[0]
            unit_data, base_unit_data = unit_data[key]['children'], base_unit_data[base_key]['children']

        data = {
            'components_data': unit_data,
            'base_components_data': base_unit_data,
        }

        return Response(data, status=status.HTTP_200_OK)

class GetCoursesVersionInfo(generics.RetrieveAPIView):
    """
    API to get ids of user courses with their translated versions

    GET meta_translations/api/v0/versions
    Response:
    {
        {
            "base_course_key_1" : {
                "id": "base_course_key_1,
                "title": "Introduction To Computing (English base course)",
                "language": "en",
                "rerun": {
                    course_key_2: {
                        "id": "course_key_2",
                        "tilte": "Introduction To Computing(Urdu)",
                        "language": "ur",
                    },
                    course_key_3: {
                        "id": "course_key_3",
                        "tilte": "Introduction To Computing(French)",
                        "language": "fr",
                    }
                }
            }
        }
    }

    For Superusers Only:
        Optional parameter can be added to filter out own created courses instead of getting all courses.
        GET meta_translations/api/v0/versions?admin_created_courses=true
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

    def _get_course_ids_list(self, request, admin_created_courses=False):
        """
        if admin_created_courses is set -> return course ids only for courses created by admin.
        otherwise -> return user accessible courses i.e
            For admin users and staff users -> return all courses.
            For normal users -> return user created courses + courses on which user is added in Course Team.
        """
        # courses accessible to users. For staff/superusers all courses will be returned.
        user_courses, _ = get_courses_accessible_to_user(request)

        # option only for superuser to filter out own created courses.
        if request.user.is_superuser and admin_created_courses:
            course_keys = []
            for course in user_courses:
                role = CourseStaffRole(course.id)
                if role.has_user(request.user, check_user_activation=False):
                    course_keys.append(course.id)
        else:
            course_keys = [course.id for course in user_courses]

        return course_keys


    def get(self, request, *args, **kwargs):
        admin_created_courses = False
        if request.user.is_superuser:
            admin_created_courses = self.request.GET.get('admin_created_courses', False)

        course_keys = self._get_course_ids_list(request, str(admin_created_courses).upper()=='TRUE')
        translated_courses = CourseTranslation.objects.filter(base_course_id__in=course_keys)
        base_course_keys = [translated_course.base_course_id for translated_course in translated_courses]
        base_course_keys = list(set(base_course_keys))
        data = [self._course_version_format(key) for key in base_course_keys]
        json_data = dict(data)
        return Response(json_data, status=status.HTTP_200_OK)

class CourseBlockViewSet(viewsets.ModelViewSet):
    """
    Viewset to update Couse Block and Wiki Translations together
    Hit this URL: /meta_translations/api/v0/<course_id>/translations/<block_id>/
    GET API:
        Response:
        {
            "block_id": "<block_id>",
            "block_type": "chapter",
            "course_id": "course-v1:Arbisoft+CS101+TranslatedRerun1",
            "approved": true,
            "wiki_translations": [
                {
                    "id": 245,
                    "target_block": 303,
                    "translation": null,
                    "approved": true,
                    "applied": false,
                    "last_fetched": null,
                    "revision": null,
                    "approved_by": 3
                }
            ]
        }
    PUT API:
        To only update the applied status of a block mentioned in url
            Request:
            {
                approved = true,
            }
        To update applied status of block and their children
            Request:
            {
                approved = true,
                apply_all = true
            }
        To update translations of a block
            Request:
            {
                approved = true,
                wiki_translations: [
                    {
                        id: <data_block_id>,
                        translation: 'new_translation'
                    },
                    {
                        id: <data_block_id>,
                        translation: 'new_translation'
                    },
                ]
            }
        Response of all put requests is same as the GET API
    """
    lookup_field = 'block_id'
    serializer_class = CourseBlockSerializer
    permission_classes = (permissions.IsAuthenticated, DestinationCourseOnly)

    def get_queryset(self):
        course_id = self.kwargs['course_key']
        return CourseBlock.objects.filter(course_id=course_id)
