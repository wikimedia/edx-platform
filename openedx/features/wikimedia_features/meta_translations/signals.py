import json

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from openedx.features.wikimedia_features.meta_translations.models import WikiTranslation
from lms.djangoapps.courseware.courses import get_course_by_id



@receiver(post_save, sender=WikiTranslation)
def add_language_and_set_mapping_update(sender, instance, created, **kwargs):
    """
    On every new Mapping Object (WikiTranslation), set update_mapping to True and update languages so that
    next send_translation cron job will sync updated blocks data to wikimedia Meta for translations.
    """
    if not created:
        return

    instance.source_block_data.mapping_updated = True
    instance.source_block_data.save()

    course = get_course_by_id(instance.target_block.course_id)
    instance.source_block_data.course_block.add_mapping_language(course.language)


@receiver(pre_delete, sender=WikiTranslation)
def remove_language_and_set_mapping_update(sender, instance, **kwargs):
    """
    On deleting Mapping Object (WikiTranslation), set update_mapping to True and update language so that next
    send_translation cron job will sync updated blocks data to wikimedia Meta for translations.
    """
    instance.source_block_data.mapping_updated = True
    instance.source_block_data.save()

    course = get_course_by_id(instance.target_block.course_id)
    instance.source_block_data.course_block.remove_mapping_language(course.language)
