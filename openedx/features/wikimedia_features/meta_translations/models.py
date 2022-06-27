
"""
Meta Translations Models
"""
import json
import jsonfield
import logging
import pytz

from config_models.models import ConfigurationModel
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField
from lms.djangoapps.courseware.courses import get_course_by_id

log = logging.getLogger(__name__)
User = get_user_model()
APP_LABEL = 'meta_translations'


class MetaTranslationConfiguration(ConfigurationModel):
    staff_show_api_buttons = models.BooleanField(default=False)
    normal_users_show_api_buttons = models.BooleanField(default=False)
    days_settings_for_fetch_call = models.IntegerField(default=0, verbose_name=_("Days settings for next Fetch call"))

    class Meta:
        app_label = APP_LABEL


class TranslationVersion(models.Model):
    """
    Store approved versions of a block to keep track of previous translations
    """
    block_id = UsageKeyField(max_length=255)
    date = models.DateTimeField(auto_now_add=True, blank=True)
    data = jsonfield.JSONField(default={}, null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)

    def get_date(self):
        """
        Returns Formated local datetime i.e Jun 10, 2022, 5:19 a.m
        """
        date = self.date
        utc = date.replace(tzinfo=pytz.UTC)
        localtz = utc.astimezone(timezone.get_current_timezone())
        return localtz.strftime('%b %d, %Y, %H:%M %P')

    class Meta:
        app_label = APP_LABEL
        unique_together = ('block_id', 'date')

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
    parent_id = UsageKeyField(max_length=255, null=True)
    block_type = models.CharField(max_length=255)
    course_id = CourseKeyField(max_length=255, db_index=True)
    direction_flag = models.CharField(blank=True, null=True, max_length=2, choices=DIRECTION_CHOICES, default=_Source)
    lang = jsonfield.JSONField(default=json.dumps([]), blank=True)
    applied_translation = models.BooleanField(default=False)
    applied_version = models.ForeignKey(TranslationVersion, null=True, blank=True, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)

    @classmethod
    def create_course_block_from_dict(cls, block_data, course_id, create_block_data=True):
        """
        Creates CourseBlock from data_dict. It will create CourseBlockData as well if create_block_data is True.
        """
        created_block = cls.objects.create(
            block_id=block_data.get('usage_key'), parent_id=block_data.get('parent_usage_key'), block_type=block_data.get('category'), course_id=course_id
        )
        # For base course blocks, create_block_datawill be True and Direction flag will be set to Default i.e Source.
        if create_block_data:
            for key, value in block_data.get('data',{}).items():
                parsed_keys = created_block.get_parsed_data(key, value)
                CourseBlockData.objects.create(course_block=created_block, data_type=key, data=value, parsed_keys=parsed_keys)
        # For translated rerun blocks Direction flag will be set to Destination on first time creation but this flag can be updated later.
        else:
            created_block.direction_flag = cls._DESTINATION
            created_block.save()
        return created_block

    def add_course_data(self, data_type, data, parsed_keys):
        """
        Add a new course data in a course block
        """
        return CourseBlockData.objects.create(course_block=self, data_type=data_type, data=data, parsed_keys=parsed_keys)

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
            log.info("Target language: {} has been added to language list.".format(language))
            self.lang = json.dumps(existing_languages)
            self.save()

    def remove_mapping_language(self, language):
        """
        Removes given language from block languages
        """
        existing_languages = json.loads(self.lang)
        if language in existing_languages:
            existing_languages.remove(language)
            log.info("Target language: {} has been removed from language list.".format(language))
            self.lang = json.dumps(existing_languages)
            self.save()

    def get_source_block(self):
        """
        Returns mapped source course block.
        """
        existing_mappings = self.wikitranslation_set.all()
        if existing_mappings:
            return existing_mappings.first().source_block_data.course_block

    def is_translations_approved(self):
        """
        Return True if all wiki_transaltions are approved
        """
        existing_mappings = self.wikitranslation_set.all()
        return all(existing_mappings.values_list("approved", flat=True))

    def get_block_info(self):
        """
        Returns block info using mapped translations.
        """
        existing_mappings = self.wikitranslation_set.all()
        if existing_mappings:
            data = existing_mappings.first().status_info()
            data['applied'] = self.applied_translation
            data['approved'] = all(existing_mappings.values_list("approved", flat=True))
            data['destination_flag'] = self.is_destination()
            return data

    def update_flag_to_source(self, target_course_language):
        """
        When block direction is updated from Destination to Source, language in linked source block will be
        updated and mapping_updated will be set to true so that on next send_translation crone job, Meta
        Server can be informed that translation of this block is not needed anymore.
        """
        if self.is_destination():
            log.info("Update flag to Source for block with id: {}, type: {}".format(
                self.block_id, self.block_type
            ))
            source_block = self.get_source_block()
            if source_block:
                log.info("Linked source block found: {} for target block: {}.".format(
                    source_block.block_id, self.block_id
                ))
                source_block.remove_mapping_language(target_course_language)
                log.info("Updated language list: {} for linked source block: {} where target block: {} and target language: {}.".format(
                    source_block.lang, source_block.block_id, self.block_id, target_course_language
                ))
                for data in source_block.courseblockdata_set.all():
                    data.mapping_updated = True
                    data.save()
            self.direction_flag = CourseBlock._Source
            self.save()
            log.info("Block with block_id {}, block_type {} has been updated to Source.".format(
                self.block_id, self.block_type
            ))
            return self
        else:
            log.info("Block with block_id {}, block_type {} is already a source block.".format(
                self.block_id, self.block_type
            ))

    def update_flag_to_destination(self, target_course_language):
        """
        When block direction is updated from Source to Destination, language in linked source block will be
        updated and mapping_updated will be set to true so that on next send_translation crone job, Meta
        Server can be informed that translation of this block is needed in this language as well.
        """
        if self.is_source():
            log.info("Update flag to Destination for block with id: {}, type: {}".format(
                self.block_id, self.block_type
            ))
            source_block = self.get_source_block()
            if source_block:
                log.info("Linked source block found: {} for target block: {}.".format(
                    source_block.block_id, self.block_id
                ))
                source_block.add_mapping_language(target_course_language)
                log.info("Updated language list: {} for linked source block: {} where target block: {} and target language: {}.".format(
                    source_block.lang, source_block.block_id, self.block_id, target_course_language
                ))
                for data in source_block.courseblockdata_set.all():
                    data.mapping_updated = True
                    data.save()
                self.direction_flag = CourseBlock._DESTINATION
                self.save()
                log.info("Block with block_id {}, block_type {} has been updated to Destination.".format(
                    self.block_id, self.block_type
                ))
                return self
        else:
            log.info("Block with block_id {}, block_type {} is already a destination block.".format(
                self.block_id, self.block_type
            ))

    def get_parsed_data(self, data_type, data):
        """
        Transform raw_data into parsed_data
        """
        if data_type in settings.DATA_TYPES_WITH_PARCED_KEYS and self.block_type in settings.TRANSFORMER_CLASS_MAPPING:
            return settings.TRANSFORMER_CLASS_MAPPING[self.block_type]().raw_data_to_meta_data(data)

    def get_snapshot(self):
        """
        Returns all translated data for a block
        {
            display_name: "Problem 1",
            content: '{"problem.optionresponse.p": "Edit this block",
                       "problem.optionresponse.label": "Add the question text"}'
        }
        """
        existing_mappings = self.wikitranslation_set.all()
        snapshot = {}
        for wikitranslation in existing_mappings:
            if wikitranslation.source_block_data.data_type in settings.DATA_TYPES_WITH_PARCED_KEYS and self.block_type in settings.TRANSFORMER_CLASS_MAPPING:
                snapshot[wikitranslation.source_block_data.data_type] = json.loads(wikitranslation.translation) if wikitranslation.translation else {}
            else:
                snapshot[wikitranslation.source_block_data.data_type] = wikitranslation.translation
        return snapshot

    def create_translated_version(self, user):
        """
        Create a version of the snapshot
        """
        snapshot = self.get_snapshot()
        version = TranslationVersion.objects.create(
            block_id = self.block_id, data = snapshot, approved_by = user)
        return version

    def get_translated_version_status(self):
        """
        Returns version status
        {
            'applied': True,
            'applied_version: 5,
            'latest_version': 10,
            'version' [
                {id: 5, date: 'Jun 10, 2022, 5:19 a.m '},
                {id: 10, date: 'Jun 15, 2022, 6:30 p.m '}
            ]
        }
        """
        versions = TranslationVersion.objects.filter(block_id=self.block_id)
        version_info = {
            'applied': self.applied_translation,
            'applied_version': self.applied_version.id if self.applied_version else None,
            'latest_version': versions.last().id if versions else None,
            'versions': [{'id': version.id, 'date': version.get_date()} for version in versions]
        }
        return version_info

    def get_latest_version(self):
        """
        Returns the last approved version of a course block
        """
        version = TranslationVersion.objects.filter(block_id=self.block_id).last()
        if version:
            return {'id': version.id, 'date': version.get_date()}

        return {}

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
    parsed_keys = jsonfield.JSONField(default=None, blank=True)
    content_updated = models.BooleanField(default=False)
    mapping_updated = models.BooleanField(default=False)

    @classmethod
    def update_base_block_data(cls, block_id, data_type, updated_data, course_block_data=None):
        """
        if base_block content is updated then
        - Sync updated data in db i.e CourseBlockData.
        - Set content_update to True so that next meta server send call would send updated content.
        - Reset all versions and translations.
        """
        from openedx.features.wikimedia_features.meta_translations.utils import reset_fetched_translation_and_version_history
        if not course_block_data:
            try:
                course_block_data = cls.objects.get(course_block__block_id=block_id, data_type=data_type)
            except cls.DoesNotExist:
                return

        course_block_data.data = updated_data
        course_block_data.parsed_keys = course_block_data.course_block.get_parsed_data(data_type, updated_data)
        course_block_data.content_updated = True
        course_block_data.save()
        reset_fetched_translation_and_version_history(course_block_data)

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
    approved = models.BooleanField(default=False)
    last_fetched = models.DateTimeField(null=True, blank=True)
    fetched_commits = jsonfield.JSONField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)

    def status_info(self):
        """
        Returns translation status
        """
        return  {
            'approved': self.approved,
            'last_fetched': self.last_fetched,
            'approved_by': self.approved_by.username if self.approved_by else self.approved_by
        }

    @classmethod
    def create_translation_mapping(cls, base_course_blocks_data, key, value, parent_id, target_block):
        try:
            target_block_usage_key = target_block.block_id
            reference_key = target_block_usage_key.block_id
            # reference key is the alphanumeric key in block_id.
            # target block and source block will contain same reference key if block is created through edX rerun.
            if reference_key:
                base_course_block_data = base_course_blocks_data.get(course_block__block_id__endswith=reference_key, data_type=key)
                if base_course_block_data.course_block.deleted:
                    log.info("Unable to create mapping for reference key {} as source block state is deleted.".format(
                        key, value, reference_key
                    ))
                    return
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
                # Check if the parent block is mapped, filter blocks based on parent_id and then compare data within those blocks
                # Otherwise compare data throughout the course 
                parent_mapping = cls.objects.filter(target_block__block_id=parent_id).first()
                base_course_block_data = None
                if parent_mapping:
                    log.info("Parent mapping found. Try compare data with along parent id")
                    base_parent_id = parent_mapping.source_block_data.course_block.block_id
                    base_course_block_data = base_course_blocks_data.get(course_block__parent_id=base_parent_id, data_type=key, data=value)
                else:
                    log.info("Couldn't found parent mapping. Try just data comparison")
                    base_course_block_data = base_course_blocks_data.get(data_type=key, data=value)
                
                if base_course_block_data.course_block.deleted:
                    log.info("Unable to create mapping for key: {}, value:{} as source block state is deleted.".format(
                        key, value
                    ))
                    return
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
                    key, value, str(target_block.course_id))
                )

    @classmethod
    def is_translation_contains_parsed_keys(cls, block_type, data_type):
        """
        Check the translation is parsed or not
        """
        if block_type in settings.TRANSFORMER_CLASS_MAPPING and data_type in settings.DATA_TYPES_WITH_PARCED_KEYS:
            return True
        return False

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

    @classmethod
    def is_base_or_translated_course(cls, course_key):
        """
        Returns string indicating if course is a base course or a translated version of some base course.
        For base course -> returns "Base"
        For translated rerun -> returns "Translated"
        else returns None
        """
        if cls.objects.filter(base_course_id=course_key).exists():
            return "Base"
        elif cls.objects.filter(course_id=course_key).exists():
            return "Translated"
        else:
            return ""

    @classmethod
    def is_base_course(cls, course_id):
        """
        Check if the course is base course of any translated rerun
        """
        return CourseTranslation.objects.filter(base_course_id=course_id).exists()

    @classmethod
    def is_translated_rerun_exists_in_language(cls, base_course_id, language):
        """
        Returns boolean value indicating if translated rerun in language already exists for given base course id.
        """
        translated_reruns_linkage = CourseTranslation.objects.filter(base_course_id=base_course_id)
        for linkage in translated_reruns_linkage:
            translated_rerun_course = get_course_by_id(linkage.course_id)
            if translated_rerun_course and translated_rerun_course.language==language:
                return True
        return False

    class Meta:
        app_label = APP_LABEL
        verbose_name = "Course Translation"
        unique_together = ('course_id', 'base_course_id')
