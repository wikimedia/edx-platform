"""
Views for wikimedia_general v0 API(s)
"""
import operator
from functools import reduce

from django.db.models import Q

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view

from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.courseware.courses import get_courses
from openedx.features.wikimedia_features.wikimedia_general.utils import get_user_completed_course_keys
from openedx.core.djangoapps.content.course_overviews.serializers import CourseOverviewBaseSerializer
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

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
        course_key_string = kwargs.get('course_key_string')
        course_key = CourseKey.from_string(course_key_string)
        course = get_course_by_id(course_key)

        data = {
            'key': course_key_string,
            'course_font': course.course_font_family,
        }

        return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_courses_to_study_next(request):
    """Endpoint to retrieve follow up courses for the user's completed courses.
    """
    user = request.user

    user_completed_course_keys = get_user_completed_course_keys(user)
    # Find courses which have courses in user_completed_course_keys as their prerequisite
    query = reduce(operator.and_, (Q(_pre_requisite_courses_json__contains=course_key) 
                                   for course_key in user_completed_course_keys)) 
    follow_up_courses = list(CourseOverview.objects.filter(query))
    serialzer = CourseOverviewBaseSerializer(follow_up_courses, many=True)
        
    return Response({"follow-up-courses": serialzer.data}, status=status.HTTP_200_OK)