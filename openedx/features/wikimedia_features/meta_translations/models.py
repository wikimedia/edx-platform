
"""
Meta Translations Models
"""
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField

APP_LABEL = 'meta_translations'


class CourseBlock(models.Model):
    """
    Store block_id(s) of base course blocks and translated reruns course blocks
    """
    block_id = models.CharField(max_length=255, unique=True)
    block_type = models.CharField(max_length=255)
    course_id = CourseKeyField(max_length=255, db_index=True)

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

    class Meta:
        app_label = APP_LABEL
        verbose_name = "Wiki Meta Translations"
        unique_together = ('target_block', 'source_block_data')
