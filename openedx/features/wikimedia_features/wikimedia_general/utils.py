import logging
import six

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey

from openedx.features.course_experience.utils import get_course_outline_block_tree
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

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
