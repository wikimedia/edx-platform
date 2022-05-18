
"""
Meta Translations Models
"""
import json
import jsonfield
import logging
import six

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

log = logging.getLogger(__name__)
User = get_user_model()
APP_LABEL = 'meta_translations'


class CourseBlock(models.Model):
    """
    Store block_id(s) of base course blocks and translated reruns course blocks
    """

    _Source = 'S'
    _DESTINATION = 'D'

    DIRECTION_CHOICES = (
        (_DESTINATION, _('Destination')),
        (_Source, _('Source')),
    )

    block_id = UsageKeyField(max_length=255, unique=True, db_index=True)
    block_type = models.CharField(max_length=255)
    course_id = CourseKeyField(max_length=255, db_index=True)
    direction_flag = models.CharField(blank=True, null=True, max_length=2, choices=DIRECTION_CHOICES, default=_Source)
    lang = jsonfield.JSONField(default=json.dumps([]))

    @classmethod
    def create_course_block_from_dict(cls, block_data, course_id, create_block_data=True):
        """
        Creates CourseBlock from data_dict. It will create CourseBlockData as well if create_block_data is True.
        """
        created_block = cls.objects.create(
            block_id=block_data.get('usage_key'), block_type=block_data.get('category'), course_id=course_id
        )
        if create_block_data:
            for key, value in block_data.get('data',{}).items():
                CourseBlockData.objects.create(course_block=created_block, data_type=key, data=value)
        else:
            created_block.direction_flag = cls._DESTINATION
            created_block.save()
        return created_block

    def add_course_data(self, data_type, data):
        """
        Add a new course data in a course block
        """
        return CourseBlockData.objects.create(course_block=self, data_type=data_type, data=data)
        
    def is_source(self):
        """
        Returns Boolean value indicating if block direction flag is Source or not
        """
        return self.direction_flag == self._Source
    
    def is_destination(self):
        """
        Returns Boolean value indicating if block direction flag is Destination or not
        """
        return self.direction_flag == self._DESTINATION

    def add_mapping_language(self, language):
        """
        Adds given language to block languages
        """
        existing_languages = json.loads(self.lang)
        if language not in existing_languages:
            existing_languages.append(language)
            self.lang = json.dumps(existing_languages)
            self.save()

    def remove_mapping_language(self, language):
        """
        Removes given language from block languages
        """
        existing_languages = json.loads(self.lang)
        if language in existing_languages:
            existing_languages.remove(language)
            self.lang = json.dumps(existing_languages)
            self.save()

    def get_source_block(self):
        """
        Returns mapped source course block.
        """
        existing_mappings = self.wikitranslation_set.all()
        if existing_mappings:
            return existing_mappings.first().source_block_data.course_block
    
    def get_block_info(self):
        """
        Returns block info using mapped translations.
        """
        existing_mappings = self.wikitranslation_set.all()
        if existing_mappings:
            return existing_mappings.first().status_info()

    def update_flag_to_source(self, target_course_language):
        """
        When block direction is updated from Destination to Source, language in linked source block will be
        updated and mapping_updated will be set to true so that on next send_translation crone job, Meta
        Server can be informed that translation of this block is not needed anymore.
        """
        if self.is_destination():
            source_block = self.get_source_block()
            if source_block:
                source_block.remove_mapping_language(target_course_language)
                for data in source_block.courseblockdata_set.all():
                    data.mapping_updated = True
                    data.save()
                self.direction_flag = CourseBlock._Source
                self.save()
                return self
    
    def update_flag_to_destination(self, target_course_language):
        """
        When block direction is updated from Source to Destination, language in linked source block will be
        updated and mapping_updated will be set to true so that on next send_translation crone job, Meta
        Server can be informed that translation of this block is needed.
        """
        if self.is_source():
            source_block = self.get_source_block()
            if source_block:
                source_block.add_mapping_language(target_course_language)
                for data in source_block.courseblockdata_set.all():
                    data.mapping_updated = True
                    data.save()
                self.direction_flag = CourseBlock._DESTINATION
                self.save()
                return self


    def apply_all_translations(self):
        """
        Apply all translations available in WikiTransaltions for a block
        """
        existing_mappings = self.wikitranslation_set.all()
        for wikitranslation in existing_mappings:
            wikitranslation.applied = True
            wikitranslation.save()

    def __str__(self):
        return str(self.block_id)
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
    parsed_keys = jsonfield.JSONField(default=None)
    content_updated = models.BooleanField(default=False)
    mapping_updated = models.BooleanField(default=False)

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
    applied = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    last_fetched = models.DateTimeField(null=True, blank=True)
    revision = models.IntegerField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    def status_info(self):
        """
        Returns translation status
        """
        return  {
            'applied': self.applied,
            'approved': self.approved,
            'last_fetched': self.last_fetched,
            'approved_by': self.approved_by.username if self.approved_by else self.approved_by,
        }
    
    @classmethod
    def create_translation_mapping(cls, base_course_blocks_data, key, value, target_block):
        try:
            target_block_usage_key = target_block.block_id
            reference_key = target_block_usage_key.block_id
            # reference key is the alphanumeric key in block_id.
            # target block and source block will contain same reference key if block is created through edX rerun.
            if reference_key:
                base_course_block_data = base_course_blocks_data.get(
                    course_block__block_id__endswith=reference_key, data_type=key, data=value)
                WikiTranslation.objects.create(
                    target_block=target_block,
                    source_block_data=base_course_block_data,
                )
                log.info("Mapping has been created for data_type {}, value {} with reference key {}".format(
                    key, value, reference_key
                ))
            else:
                raise CourseBlockData.DoesNotExist
        except CourseBlockData.DoesNotExist:
            log.info("Unable to create mapping with reference key {}. Try again with data comparison.".format(
                reference_key
            ))
            try:
                # For target blocks - added after rerun creation.
                base_course_block_data = base_course_blocks_data.get(data_type=key, data=value)
                WikiTranslation.objects.create(
                    target_block=target_block,
                    source_block_data=base_course_block_data,
                )
                log.info("Mapping has been created for data_type {}, value {}".format(key, value))

            except CourseBlockData.MultipleObjectsReturned:
                log.error("Error -> Unable to find source block mapping as multiple source blocks found"
                          "in data comparison - data_type {}, value {}".format(key, value))
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

    @classmethod
    def get_base_courses_list(cls):
        """
        Returns list of course_id(s) that has translated rerun version
        """
        return cls.objects.all().values_list("base_course_id", flat=True).distinct()

    class Meta:
        app_label = APP_LABEL
        verbose_name = "Course Translation"
        unique_together = ('course_id', 'base_course_id')
