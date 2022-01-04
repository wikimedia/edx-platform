
import six

from django.test import RequestFactory
from opaque_keys.edx.keys import CourseKey

from openedx.features.course_experience.utils import get_course_outline_block_tree


def is_course_graded(course_id, user, request=None):
    """
    Check that course is graded.

    Arguments:
        course_id: (CourseKey/String) if CourseKey turn it into string
        request: (WSGI Request/None) if None create your own dummy request object

    Returns:
        is_graded (bool)
    """
    if request is None:
        request = RequestFactory().get(u'/')
        request.user = user

    if isinstance(course_id, CourseKey):
        course_id = six.text_type(course_id)

    course_outline = get_course_outline_block_tree(request, course_id, user)

    if course_outline:
        return course_outline.get('num_graded_problems') > 0
    else:
        return False
