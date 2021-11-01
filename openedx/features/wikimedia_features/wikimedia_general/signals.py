"""
Signals for clearesult features django app.
"""
from logging import getLogger

from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save

from common.djangoapps.course_modes.models import CourseMode
from xmodule.modulestore.django import SignalHandler
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

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
