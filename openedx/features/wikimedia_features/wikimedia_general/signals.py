"""
Signals for clearesult features django app.
"""
import mimetypes
import os
from logging import getLogger

from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from opaque_keys.edx.keys import CourseKey
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile

from django.contrib.sites.models import Site
from common.djangoapps.course_modes.models import CourseMode
from xmodule.modulestore.django import SignalHandler
from openedx.core.djangoapps.django_comment_common.signals import (
    comment_created, comment_edited, thread_created, thread_edited, 
)
from openedx.core.djangoapps.theming.helpers import get_current_site
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.features.wikimedia_features.wikimedia_general.utils import (
    is_discussion_notification_configured_for_site,
    add_courseware_info
)
from openedx.features.wikimedia_features.wikimedia_general.tasks import send_thread_mention_email_task, send_thread_creation_email_task
from openedx.features.wikimedia_features.email.utils import (
    update_context_with_thread,
    update_context_with_comment,
    build_discussion_notification_context
)

from cms.djangoapps.contentstore.exceptions import AssetSizeTooLargeException

logger = getLogger(__name__)

@receiver(post_save, sender=CourseOverview)
def upload_course_default_image(sender, instance, created, **kwargs):
    if created:
        course_key=instance.id
        file_path = finders.find('images/course_default_image/images_course_image.jpg')
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    content_type, _ = mimetypes.guess_type(file_path)
                    django_file = SimpleUploadedFile(name=os.path.basename(file_path),
                                                    content=file.read(),
                                                    content_type=content_type)
                    from cms.djangoapps.contentstore.views.assets import update_course_run_asset
                    content = update_course_run_asset(course_key, django_file)
                    logger.info("File processing completed for course: %s", course_key)
            else:
                logger.error("File does not exist at path: %s", file_path)
        except AssetSizeTooLargeException as e:
            logger.error("Asset size too large for course %s: %s", course_key, str(e))
        except Exception as e:
            logger.error("Error processing file for course %s: %s", course_key, str(e))
    
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

@receiver(comment_created)
@receiver(comment_edited)
@receiver(thread_edited)
@receiver(thread_created)
def send_thread_mention_email_notification(sender, user, post, **kwargs):
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
    current_site = get_current_site()
 
    if current_site is None:
        current_site = Site.objects.get_current()
 
    is_thread = post.type == 'thread'
    if not is_discussion_notification_configured_for_site(current_site, post.id):
        return
    course_key = CourseKey.from_string(post.course_id)
    # course_overview = CourseOverview.get_from_id(post.course_id)
    # course_name = course_overview.display_name
    context = {
        'course_id': course_key,
        # 'course_name':course_name,
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
