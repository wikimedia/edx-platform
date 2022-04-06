"""
Signals for Meta Translations
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from logging import getLogger

from openedx.features.wikimedia_features.meta_translations.models import CourseBlockData, WikiTranslation

log = getLogger(__name__)

@receiver(pre_save, sender=CourseBlockData)
def on_change(sender, instance, **kwargs):
    """
    On updating data of CourseBlockData table, reset respective wiki translations
    """
    if instance.id:
        WikiTranslation.objects.filter(source_block_data__id=instance.id).update(sent=False, translation=None)
        log.info("Wiki Translations are reset for Course Block Data {}".format(instance.id))
