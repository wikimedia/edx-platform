import logging
import six
import operator
from functools import reduce

from django.db.models import Q
import pytz
import copy

from datetime import datetime, timedelta
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from common.djangoapps.student.models import CourseEnrollment
from opaque_keys.edx.keys import CourseKey

from openedx.features.course_experience.utils import get_course_outline_block_tree
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from lms.djangoapps.grades.api import CourseGradeFactory
from common.djangoapps.student.views import get_course_enrollments, get_org_black_and_whitelist_for_site

log = logging.getLogger(__name__)
User = get_user_model()
ENABLE_FORUM_NOTIFICATIONS_FOR_SITE_KEY = 'enable_forum_notifications'


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

def is_discussion_notification_configured_for_site(site, post_id):
    if site is None:
        log.info('Discussion: No current site, not sending notification about new thread: %s.', post_id)
        return False
    try:
        if not site.configuration.get_value(ENABLE_FORUM_NOTIFICATIONS_FOR_SITE_KEY, False):
            log_message = 'Discussion: notifications not enabled for site: %s. Not sending message about new thread: %s'
            log.info(log_message, site, post_id)
            return False
    except SiteConfiguration.DoesNotExist:
        log_message = 'Discussion: No SiteConfiguration for site %s. Not sending message about new thread: %s.'
        log.info(log_message, site, post_id)
        return False
    return True


def get_mentioned_users_list(input_string, users_list=None):
    if not users_list:
        users_list = []

    start_index = input_string.find("@")
    if start_index == -1:
        return users_list
    else:
        end_index = input_string[start_index:].find(" ")
        name = input_string[start_index:][:end_index]

        try:
            user = User.objects.get(username=name[1:]) #remove @ from name
            users_list.append(user)
        except User.DoesNotExist:
            log.error("Unable to find mentioned thread user with name: {}".format(name))

        # remove tagged name from string and search for next tagged name
        remianing_string = input_string.replace(name, "")
        return get_mentioned_users_list(remianing_string, users_list)


def get_user_enrollments_course_keys(user):
    course_limit = None
    # Get the org whitelist or the org blacklist for the current site
    site_org_whitelist, site_org_blacklist = get_org_black_and_whitelist_for_site()
    course_enrollments = list(get_course_enrollments(user, site_org_whitelist, site_org_blacklist, course_limit))
    course_enrollments_keys = [enrollment.course_id for enrollment in course_enrollments]
    
    return course_enrollments_keys


def is_course_completed(user, course_key):
    if isinstance(course_key, str):
        course_key = CourseKey.from_string(course_key)
    return CourseGradeFactory().read(user, course_key=course_key).summary['grade'] == 'Pass'


def get_user_completed_course_keys(user):
    """
    Get courses that the user has completed.
    """
    course_enrollments_keys = get_user_enrollments_course_keys(user)

    return ['{}'.format(course_key) for course_key in course_enrollments_keys if is_course_completed(user, course_key)]


def get_follow_up_courses(course_keys):
    """
    Returns courses which have courses in course_keys as their prerequisite
    """
    follow_up_courses = []

    if course_keys:
        course_keys_in_prerequisites = (Q(_pre_requisite_courses_json__contains=course_key)
                                        for course_key in course_keys)
        query = reduce(operator.or_, course_keys_in_prerequisites)
        follow_up_courses = list(CourseOverview.objects.filter(query))

    return follow_up_courses


def get_users_enrollment_stats(users_enrollments, course_keys):
    """Returns stats based on users enrollments
    dict: 
        students_enrolled_in_any_course
        students_enrolled_in_all_courses
    """
    enrollment_stats = {
        "students_enrolled_in_any_course": 0,
        "students_enrolled_in_all_courses": 0
    }
    for enrollments in users_enrollments.values():
        if enrollments: # If user has any enrollments
            enrollment_stats['students_enrolled_in_any_course'] += 1
        if enrollments >= course_keys:
            enrollment_stats['students_enrolled_in_all_courses'] += 1
        
    return enrollment_stats


def get_users_course_completion_stats(users, users_enrollments, course_keys):
    """Returns stats about course completion based on users enrollments
    dict: 
        students_completed_any_course: number
        students_completed_all_courses: number
    """
    users_course_completion = dict()
    for user in users:
        users_course_completion[user.id] = set(filter(lambda course_key: is_course_completed(user, course_key),
                                                users_enrollments[user.id]))
    course_completion_stats = {
        "students_completed_any_course": 0,
        "students_completed_all_courses": 0
    }
    for course_completions in users_course_completion.values():
        if course_completions:
            course_completion_stats['students_completed_any_course'] += 1
        if course_completions >= course_keys:
            course_completion_stats['students_completed_all_courses'] += 1

    return course_completion_stats


def get_course_enrollment_and_completion_stats(course_id) -> dict:
    """Returns the count of student completed the provided course
    """
    enrollments = CourseEnrollment.objects.filter(
            course_id=course_id,
            is_active=True,
        )

    total_students_completed = 0
    for enrollment in enrollments:
        user = User.objects.get(id=enrollment.user_id)
        if is_course_completed(user, course_id):
            total_students_completed += 1

    enrollment_count = enrollments.count()
    percentage_completed = (total_students_completed/enrollment_count) * 100 if enrollment_count else 0

    return (total_students_completed, enrollment_count, percentage_completed)


def get_paced_type(self_paced):
    """ Paced Type Filter
    Args:
        self_paced (Bool): Self paced or Instructor Led
    Returns:
        str: paced type
    """
    return 'self_paced' if self_paced else 'instructor_led'


def get_prerequisites_type(pre_requisite_courses):
    """ Prerequisites Filter
    Args:
        pre_requisite_courses (list): List of prerequisites
    Returns:
        str: Prerequisites Type
    """
    return 'require_prerequisites' if len(pre_requisite_courses) else 'no_prerequisites'


def get_enrollment_type(enrollment_date):
    """ Enrollment Filter
    Args:
        enrollment_date (DateTime): Enrollment start date
    Returns:
        string: enrollment type
    """
    if enrollment_date:
        today = datetime.now(pytz.utc)
        three_months_from_today = today + timedelta(days=3*30)
        if enrollment_date <= today:
            return 'enrollment_open'
        elif enrollment_date <= three_months_from_today:
            return 'enrollment_open_in_coming_three_months'
        return 'enrollment_open_after_three_months'
    return None


def _get_studio_filters(courses):
    """
    courses (List): Courses List 
    """
    studio_filters={
        'org': {},
        'language': {},
    }
    languages = dict(settings.ALL_LANGUAGES)

    for course in courses:
        if course['org'] and course['org'] not in studio_filters['org']:
            studio_filters['org'].update({course['org']: course['org']})
        if course['language'] and course['language'] not in studio_filters['language']:
            studio_filters['language'].update({course['language']: languages[course['language']]})
    return studio_filters


def get_updated_studio_filter_meanings(courses):
    """
    Update STUDIO_FILTERS_MEANINGS from courses' contexts
    """
    studio_filters = _get_studio_filters(courses)
    studio_filters_meanings = copy.deepcopy(settings.STUDIO_FILTERS_MEANINGS)
    for studio_filter in studio_filters_meanings:
        if studio_filter in studio_filters:
            studio_filters_meanings[studio_filter]['terms'] = studio_filters[studio_filter]
    return studio_filters_meanings


WIKI_LMS_FILTER_MAPPINGS = {
    'paced_type': get_paced_type,
    'enrollment_type': get_enrollment_type,
    'prerequisites_type': get_prerequisites_type,
}
