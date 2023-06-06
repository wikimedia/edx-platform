"""
Views for wikimedia_general v0 API(s)
"""
from django.contrib.auth.decorators import login_required

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view

from opaque_keys.edx.keys import CourseKey

from django.utils.translation import ugettext as _
from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.wikimedia_general.utils import (
    get_follow_up_courses,
    get_user_completed_course_keys
)
from openedx.core.djangoapps.content.course_overviews.serializers import CourseOverviewBaseSerializer
from openedx.features.wikimedia_features.wikimedia_general.api.v0.utils import get_authenticated_header_tabs, get_unauthenticated_header_tabs

class RetrieveWikiMetaData(generics.RetrieveAPIView):
    """
    API to get course font
    Response:
        {
            "key": String,
            "course_font": String, 

        }
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        Returns course Meta Data
        """
        course_key_string = kwargs.get('course_key_string')
        course_key = CourseKey.from_string(course_key_string)
        course = get_course_by_id(course_key)

        data = {
            'key': course_key_string,
            'course_font': course.course_font_family,
        }

        return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@login_required
def get_courses_to_study_next(request):
    """Endpoint to retrieve follow up courses for the user's completed courses.
    """
    user = request.user

    user_completed_course_keys = get_user_completed_course_keys(user)
    follow_up_courses = get_follow_up_courses(user_completed_course_keys)
    serialzer = CourseOverviewBaseSerializer(follow_up_courses, many=True)

    return Response({"follow-up-courses": serialzer.data}, status=status.HTTP_200_OK)

class RetrieveLMSTabs(generics.RetrieveAPIView):
    """
    API to get LMS tabs
    Response:
        {
            "tabs: [
                {
                    "id": String,
                    "name": String,
                    "url": URL
                },
                ...
            ]
        }
    """

    def get(self, request, *args, **kwargs):
        """
        Return header tabs for MFEs
        This API is particularly made for getting Authenticated header tabs
        """
        header_tabs = []
        if request.user.is_authenticated:
            header_tabs = get_authenticated_header_tabs(request.user)
        else:
            header_tabs = get_unauthenticated_header_tabs()

        return Response({'tabs': header_tabs}, status=status.HTTP_200_OK)
