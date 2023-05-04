"""
Views for wikimedia_general v0 API(s)
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.courses import get_course_by_id


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
