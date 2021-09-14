import json
import logging

from edx_ace import ace
from edx_ace.recipient import Recipient
from django.conf import settings

from openedx.core.djangoapps.ace_common.template_context import get_base_template_context
from openedx.core.djangoapps.theming.helpers import get_current_site
from openedx.core.lib.celery.task_utils import emulate_http_request

from openedx.features.wikimedia_features.emails.constants import MESSAGE_TYPES

logger = logging.getLogger(__name__)


def send_ace_message(request_user, request_site, dest_email, context, message_class):
    context.update({'site': request_site})

    with emulate_http_request(site=request_site, user=request_user):
        message = message_class().personalize(
            recipient=Recipient(username='', email_address=dest_email),
            language='en',
            user_context=context,
        )
        logger.info('Sending email notification with context %s', context)

        ace.send(message)


def send_notification(message_type, data, subject, dest_emails, request_user, current_site=None):
    """
    Send an email
    Arguments:
        message_type - string value to select ace message object
        data - Dict containing context/data for the template
        subject - Email subject
        dest_emails - List of destination emails
    Returns:
        a boolean variable indicating email response.
    """
    if not current_site:
        current_site = get_current_site()

    data.update({'subject': subject})

    message_context = get_base_template_context(current_site)
    message_context.update(data)

    content = json.dumps(message_context)

    message_class = MESSAGE_TYPES[message_type]
    return_value = False

    base_root_url = current_site.configuration.get_value('LMS_ROOT_URL')
    logo_path = current_site.configuration.get_value(
        'LOGO',
        settings.DEFAULT_LOGO
    )

    platform_name = current_site.configuration.get_value('platform_name')
    message_context.update({
        "copyright_site_name": platform_name,
        "site_name":  current_site.configuration.get_value('SITE_NAME'),
        "logo_url": u'{base_url}{logo_path}'.format(base_url=base_root_url, logo_path=logo_path),
        "dashboard_url": "{}{}".format(base_root_url, message_context.get('dashboard_url'))
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
            return_value = True
        except Exception as e:
            logger.error(
                'Unable to send an email to %s for content "%s".',
                email,
                content,
            )
            logger.error(e)

    return return_value
