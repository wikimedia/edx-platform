"""
Signals for clearesult features django app.
"""
from logging import getLogger

from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from opaque_keys.edx.keys import CourseKey

from common.djangoapps.course_modes.models import CourseMode
from xmodule.modulestore.django import SignalHandler
from openedx.core.djangoapps.django_comment_common.signals import (
    comment_created, comment_edited, thread_created, thread_edited, 
)
from openedx.core.djangoapps.theming.helpers import get_current_site
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.features.wikimedia_features.wikimedia_general.utils import (
    is_discussion_notification_configured_for_site
)
from openedx.features.wikimedia_features.wikimedia_general.tasks import send_thread_mention_email_task, send_thread_creation_email_task
from openedx.features.wikimedia_features.email.utils import (
    update_context_with_thread,
    update_context_with_comment,
    build_discussion_notification_context
)

logger = getLogger(__name__)

@receiver(post_save, sender=CourseOverview)
def create_default_course_mode(sender, instance, created, **kwargs):
    if created:
        if not settings.FEATURES.get('ENABLE_DEFAULT_COURSE_MODE_CREATION', False):
            logger.info('Flag is not set - Skip Auto creation of default course mode.')
            return

        default_mode_slug = settings.COURSE_MODE_DEFAULTS['slug']
        if default_mode_slug != "audit":
            logger.info('Generating Default Course mode: {}'.format(default_mode_slug))
            course_mode = CourseMode(
                course=instance,
                mode_slug=default_mode_slug,
                mode_display_name=settings.COURSE_MODE_DEFAULTS['name'],
                min_price=settings.COURSE_MODE_DEFAULTS['min_price'],
                currency=settings.COURSE_MODE_DEFAULTS['currency'],
                expiration_date=settings.COURSE_MODE_DEFAULTS['expiration_datetime'],
                description=settings.COURSE_MODE_DEFAULTS['description'],
                sku=settings.COURSE_MODE_DEFAULTS['sku'],
                bulk_sku=settings.COURSE_MODE_DEFAULTS['bulk_sku'],
            )
            course_mode.save()
        else:
            logger.info('Default mode set is Audit - no need to change course mode.')

@receiver(thread_created)
def handle_thread_creation_notifications(sender, user, post, **kwargs):
    """
    Handles the sending of email notifications upon the creation of a discussion thread.

    This function is triggered when a new discussion thread is created. It fetches the
    current site context and then delegates the responsibility of sending out different
    types of email notifications to specific functions.

    Args:
        sender: The model class that sent the signal.
        user: The user who created the discussion thread.
        post: The discussion thread that was created.
        **kwargs: Additional keyword arguments.

    Note:
        This function serves as a central point for handling all notifications related
        to thread creation. It ensures that the current site is determined only once and 
        then passes this information to the functions responsible for individual 
        notification types.
    """
    current_site = get_current_site()
    if current_site is None:
        logger.error("Current site could not be determined.")
        return

    send_thread_mention_email_notification(sender, user, post, current_site, **kwargs)
    send_new_post_email_notification_to_instructors(sender, user, post, current_site, **kwargs)

@receiver(comment_created)
@receiver(comment_edited)
@receiver(thread_edited)
def send_thread_mention_email_notification(sender, user, post,current_site, **kwargs):
    """
    This function will retrieve list of tagged usernames from discussion post/response
    and then send email notifications to all tagged usernames.
    Arguments:
        sender: Model from which we received signal (we are not using it in this case).
        user: Thread/Comment owner
        post: Thread/Comment that is being created/edited
        current_site: The current site of the discussion
        kwargs: Remaining key arguments of signal.
    """
    is_thread = post.type == 'thread'
    if not is_discussion_notification_configured_for_site(current_site, post.id):
        return
    course_key = CourseKey.from_string(post.course_id)
    context = {
        'course_id': course_key,
        'site': current_site,
        'is_thread': is_thread
    }

    if is_thread:
        update_context_with_thread(context, post)
    else:
        update_context_with_thread(context, post.thread)
        update_context_with_comment(context, post)
    message_context = build_discussion_notification_context(context)
    send_thread_mention_email_task.delay(post.body, message_context, is_thread)
    
def send_new_post_email_notification_to_instructors(sender, user, post, current_site, **kwargs):
    """
    Sends email notification to course instructors when a new discussion post is created.

    Args:
        sender: The sender of the signal.
        user: The user who created the post.
        post: The newly created discussion post.
        current_site: The current site of the discussion
        **kwargs: Additional keyword arguments.

    Returns:
        None
    """
    
    if post.type != 'thread':
        return

    if not is_discussion_notification_configured_for_site(current_site, post.id):
        return

    post_id = post.course_id
    course_key = CourseKey.from_string(post.course_id)
    
    context = {
        'course_id': course_key,
        'site': current_site,
        'is_thread': True
    }
    
    update_context_with_thread(context, post)
    message_context = build_discussion_notification_context(context)
    
    send_thread_creation_email_task.delay(message_context, True, post_id)
    
    logger.info("signal successful;")


