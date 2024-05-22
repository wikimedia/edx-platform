from logging import getLogger

from celery import task
from celery_utils.logged_task import LoggedTask
from opaque_keys.edx.keys import CourseKey

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from openedx.core.djangoapps.theming.helpers import get_current_site
from openedx.features.wikimedia_features.email.utils import (
    build_discussion_notification_context,
    send_thread_creation_email,
    send_thread_mention_email,
    update_context_with_thread,
)
from openedx.features.wikimedia_features.wikimedia_general.utils import (
    get_mentioned_users_list,
    get_users_with_forum_roles,
    is_discussion_notification_configured_for_site,
)

import markdown

log = getLogger(__name__)

@task(base=LoggedTask)
def send_thread_mention_email_task(post_body, context, is_thread):
    log.info("Initiated task to send thread mention notifications.")

    # convert markdown post_body to html
    processed_post_body = markdown.markdown(post_body)

    # Replace few chars to handle cases i.e "<h1>@username</h1>" or <h1>@username/n</h1> so it will be easy
    # to retrieve mentioned usernames as usernames will be in between '@' and ' ' characters in processed_post_body.
    processed_post_body = processed_post_body.replace("\n", " ").replace("</", " ")

    users_list = get_mentioned_users_list(processed_post_body)

    if users_list:
        receipients = [user.email for user in users_list]
        send_thread_mention_email(receipients, context, is_thread)
    else:
        log.info("No user is tagged on thread/comment of discussion forum.")


@task(base=LoggedTask)
def send_thread_creation_email_task(contexts, is_thread, post_id):
    """
    Task to send email notifications for thread mentions in a discussion forum.

    Args:
        post_body (str): The content of the post that triggered the notification.
        context: information related to the post, author and site
        is_thread (bool): Indicates whether the post is a thread.
        post_id (str): The identifier for the course.

    Returns:
        None

    Example:
        send_thread_creation_email_task("Hello, this is a post.", context, True, "course_id")
    """
    log.info("Initiated task to send thread mention notifications.")

    users_list = get_users_with_forum_roles(post_id)

    if users_list:
        receipients = [user.email for user in users_list]
        send_thread_creation_email(receipients, contexts, is_thread)
    else:
        log.info("No user is tagged on thread/comment of discussion forum.")



@task(base=LoggedTask)
def send_weekly_digest_new_post_notification_to_instructors(threads):
    """
    Asynchronously sends email notifications to course instructors about new discussion posts created.
    This function is designed to process a list of discussion posts (threads), verify if notifications
    are configured for the site and the post type, and queue emails for eligible posts.

    Args:
        threads (list): A list of thread objects, each representing a discussion post. These threads are
                        expected to have properties like `type`, `course_id`, and methods like `to_dict()`.

    Returns:
        None

    Processes each thread in the given list, checking if it is of type 'thread' and if notifications are
    enabled for the post's associated site and course. Builds context for each valid thread and queues 
    a batch email sending task if there are any threads to notify.

    Each thread's context includes the course key, the site, and whether it's a thread. The function logs
    information about each processed thread and about the queuing of notifications.
    """
    current_site = get_current_site()
    if current_site is None:
        current_site = Site.objects.get_current()
    
    contexts = []
    message_contexts = []

    for post in threads:
        if post.type != 'thread':
            continue

        if not is_discussion_notification_configured_for_site(current_site, post.id):
            continue

        post_id = post.course_id
        course_key = CourseKey.from_string(post.course_id)
        data = post.to_dict()
        
        context = {
            'course_id': course_key,
            'site': current_site,
            'is_thread': True,
        }
        
        update_context_with_thread(context, post)
        message_context = build_discussion_notification_context(context)

        if 'courseware_url' in data:
            message_context['post_link'] = data['courseware_url']

        contexts.append(context)
        message_contexts.append(message_context)

        log.info(f"Prepared notification for thread ID: {post.id}, Title: {post.title}")

    if message_contexts:
        # Assumes send_thread_creation_email_task can handle lists of contexts and post IDs
        send_thread_creation_email_task.delay(message_contexts, True, post_id)
        log.info("Notifications queued for recent threads.")

    else:
        log.info("No recent threads to notify.")

