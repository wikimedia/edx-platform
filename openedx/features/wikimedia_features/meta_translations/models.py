
"""
Meta Translations Models
"""
import json
import logging
import six
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField

log = logging.getLogger(__name__)
APP_LABEL = 'meta_translations'


class CourseBlock(models.Model):
    """
    Store block_id(s) of base course blocks and translated reruns course blocks
    """
    block_id = models.CharField(max_length=255, unique=True)
    block_type = models.CharField(max_length=255)
    course_id = CourseKeyField(max_length=255, db_index=True)

    @classmethod
    def create_course_block_from_dict(cls, block_data, course_id, create_block_data=True):
        created_block = cls.objects.create(block_id=block_data.get('usage_key'), block_type=block_data.get('category'), course_id=course_id)
        if create_block_data:
            for key, value in block_data.get('data',{}).items():
                CourseBlockData.objects.create(course_block=created_block, data_type=key, data=value)
        return created_block

    def __str__(self):
        return self.block_id
    class Meta:
        app_label = APP_LABEL
        verbose_name = "Course Block"


class CourseBlockData(models.Model):
    """
    Store data/content of source blocks that need to be translated
    """
    course_block = models.ForeignKey(CourseBlock, on_delete=models.CASCADE)
    data_type = models.CharField(max_length=255)
    data = models.TextField()

    def __str__(self):
        return "{} -> {}: {}".format(
            self.course_block.block_type,
            self.data_type,
            self.data[:30]
        )

    class Meta:
        app_label = APP_LABEL
        verbose_name = "Course Block Data"
        unique_together = ('course_block', 'data_type')


class WikiTranslation(models.Model):
    """
    Store translations fetched from wiki learn meta, will also manage mapping of source and target blocks.
    """
    target_block = models.ForeignKey(CourseBlock, on_delete=models.CASCADE)
    source_block_data = models.ForeignKey(CourseBlockData, on_delete=models.CASCADE)
    translation = models.TextField(null=True, blank=True)
    sent = models.BooleanField(default=False)
    applied = models.BooleanField(default=False)
    overwrite = models.BooleanField(default=False)
    last_fetched = models.DateTimeField(null=True, blank=True)

    @classmethod
    def create_translation_mapping(cls, base_course_blocks_data, key, value, target_block):
        try:
            base_course_block_data = base_course_blocks_data.get(data_type=key, data=value)
            WikiTranslation.objects.create(
                target_block=target_block,
                source_block_data=base_course_block_data,
            )
            log.info("Mapping has been created for data_type {}, value {}".format(key, value))
        except CourseBlockData.DoesNotExist:
            log.error("Error -> Unable to find source block mapping for key {}, value {} of course: {}".format(
                key, value, six.text_type(target_block.course_id))
            )

    class Meta:
        app_label = APP_LABEL
        verbose_name = "Wiki Meta Translations"
        unique_together = ('target_block', 'source_block_data')

class CourseTranslation(models.Model):
    """
    Strores the relation of base course and translated course
    """
    course_id = CourseKeyField(max_length=255, db_index=True)
    base_course_id = CourseKeyField(max_length=255, db_index=True)

    @classmethod
    def set_course_translation(cls, course_key, source_key):
        """
        updete course translation table
        """
        course_id = str(course_key)
        base_course_id = str(source_key)
        cls.objects.create(course_id=course_id,base_course_id=base_course_id)

    class Meta:
        app_label = APP_LABEL
        verbose_name = "Course Translation"
        unique_together = ('course_id', 'base_course_id')
