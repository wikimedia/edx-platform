import markdown
import json
import logging

from opaque_keys.edx.keys import CourseKey

from edx_ace import ace
from edx_ace.utils import date
from edx_ace.recipient import Recipient
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model

from lms.djangoapps.discussion.tasks import _get_thread_url
from openedx.core.djangoapps.ace_common.template_context import get_base_template_context
from openedx.core.lib.celery.task_utils import emulate_http_request
from openedx.features.wikimedia_features.email import message_types
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

logger = logging.getLogger(__name__)
User = get_user_model()

MESSAGE_TYPES = {
  'pending_messages': message_types.PendingMessagesNotification,
  'thread_mention': message_types.ThreadMentionNotification,
  'report_ready': message_types.ReportReadyNotification,
  'thread_creation': message_types.ThreadCreationNotification
}


def send_ace_message(request_user, request_site, dest_email, context, message_class):
    with emulate_http_request(site=request_site, user=request_user):
        message = message_class().personalize(
            recipient=Recipient(lms_user_id=0, email_address=dest_email),
            language='en',
            user_context=context,
        )
        logger.info('Sending email notification with context %s', context)
        ace.send(message)


def send_notification(message_type, data, subject, dest_emails, request_user=None, current_site=None):
    """
    Send an email
    Arguments:
        message_type - string value to select ace message object
        data - Dict containing context/data for the template
        subject - Email subject
        dest_emails - List of destination emails
    Returns:
        a boolean variable indicating email response.
        if email is successfully send to all dest emails -> return True otherwise return false.
    """
    if not current_site:
        current_site = Site.objects.all().first()

    if not request_user:
        try:
            request_user = User.objects.get(username=settings.EMAIL_ADMIN)
        except User.DoesNotExist:
            logger.error(
                "Unable to send email as Email Admin User with username: {} does not exist.".format(settings.EMAIL_ADMIN)
            )
            return

    data.update({'subject': subject})

    message_context = get_base_template_context(current_site)
    message_context.update(data)
    content = json.dumps(message_context)

    message_class = MESSAGE_TYPES[message_type]
    return_value = True

    base_root_url = current_site.configuration.get_value('LMS_ROOT_URL')

    message_context.update({
        "site_name":  current_site.configuration.get_value('platform_name'),
        "logo_url": current_site.configuration.get_value('DEFAULT_EMAIL_LOGO_URL', settings.DEFAULT_EMAIL_LOGO_URL),
        "messenger_url": u'{base_url}{messenger_path}'.format(base_url=base_root_url, messenger_path=reverse("messenger:messenger_home"))
    })
    for email in dest_emails:
        message_context.update({
            "email": email
        })
        try:
            send_ace_message(request_user, current_site, email, message_context, message_class)
            logger.info(
                'Email has been sent to "%s" for content %s.',
                email,
                content
            )
        except Exception as e:
            logger.error(
                'Unable to send an email to %s for content "%s"',
                email,
                content
            )
            logger.error(e)
            return_value = False

    return return_value

def update_context_with_thread(context, thread):
    thread_author = User.objects.get(id=thread.user_id)
    context.update({
        'thread_id': thread.id,
        'thread_title': thread.title,
        'thread_body': markdown.markdown(thread.body),
        'thread_commentable_id': thread.commentable_id,
        'thread_author_id': thread_author.id,
        'thread_username': thread_author.username,
        'thread_created_at': thread.created_at
    })

def update_context_with_comment(context, comment):
    comment_author = User.objects.get(id=comment.user_id)
    context.update({
        'comment_id': comment.id,
        'comment_body': markdown.markdown(comment.body),
        'comment_author_id': comment_author.id,
        'comment_username': comment_author.username,
        'comment_created_at': comment.created_at
    })

def build_discussion_notification_context(context):
    site = context['site']
    message_context = get_base_template_context(site)
    message_context.update(context)
    message_context.update({
        'site_id': site.id,
        'post_link': _get_thread_url(context),
        'course_name': CourseOverview.get_from_id(message_context.pop('course_id')).display_name
    })
    message_context.pop('site')
    return message_context

def send_unread_messages_email(user, user_context):
    subject = "Unread Messages"
    logger.info("Sending messenger pending msgs email to the users: {}".format(user))
    key = "pending_messages"
    name = user.username
    if user.first_name:
        name = user.first_name + " " + user.last_name
    data = {"name": name,}
    data.update(user_context)
    send_notification(key, data, subject, [user.email])

def send_thread_mention_email(receivers, context, is_thread=True):
    logger.info("Sending thread mention email to users: {}".format(receivers))
    key = "thread_mention"

    if is_thread:
        mentioned_by = context.get("thread_username")
    else:
        mentioned_by = context.get("comment_username")

    context.update({
        "mentioned_by": mentioned_by,
    })

    send_notification(key, context, "", receivers)

def send_thread_creation_email(receivers, context, is_thread=True):
    """
    Send email notifications for thread mentions.

    Args:
        receivers (list): A list of email addresses to send the notifications to.
        context (dict): A dictionary containing context information for the email.
        is_thread (bool, optional): Indicates whether the post is a thread. Defaults to True.

    Returns:
        None
    """
    logger.info("Sending thread mention email to users: {}".format(receivers))
    key = "thread_creation"

    if is_thread:
        created_by = context.get("thread_username")

    context.update({
        "created_by": created_by,
    })
    send_notification(key, context, "", receivers)
