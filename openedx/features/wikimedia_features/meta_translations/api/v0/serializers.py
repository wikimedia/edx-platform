"""
Serializers for Meta-Translations v0 API(s)
"""
from django.utils.translation import ugettext as _

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.api.v0.utils import update_edx_block_from_version, validated_and_sort_translated_decodings
from openedx.features.wikimedia_features.meta_translations.meta_client import WikiMetaClient
from openedx.features.wikimedia_features.meta_translations.models import (
    CourseBlock, TranslationVersion, WikiTranslation, CourseTranslation, CourseBlockData,
)
from openedx.features.wikimedia_features.meta_translations.utils import validate_transaltions
from rest_framework import serializers


class CourseBlockTranslationSerializer(serializers.ModelSerializer):
    """
    Serializer for a courseblock
    """
    approved = serializers.BooleanField(required=False, write_only=True, default=True)


    def _validate_data(self, instance, data):
        """
        Check that the start is before the stop.
        """
        if instance.is_translations_approved() and data['approved']:
            raise serializers.ValidationError("block {} is already approved".format(instance.block_id))
        return data

    def to_representation(self, instance):
        """
        Add approved field in block. True if all the translations are approved else false
        We also need latest version that is approved
        """
        data = super(CourseBlockTranslationSerializer, self).to_representation(instance)
        data['approved'] = instance.is_translations_approved()
        data['applied_version_date'] = instance.applied_version.get_date()
        return data

    def _user(self):
        """
        Get user from request
        """
        request = self.context.get('request', None)
        if request:
            return request.user
    
    def _update_translations_fields(self, instances, approved, user):
        """
        Update WikiTranslation instances with approved and user fields
        Note: It'll apply same fields to all the instances
        """
        for instance in instances:
            instance.approved = approved
            instance.approved_by = user
            instance.save()

    def update(self, instance, validated_data):
        """
        Update the approve status of all wikitranslations belogs to a translated block, default value of approved is True
        Create a version of a course and update applid_translation and applied_version fields of a block 
        """
        if self._validate_data(instance, validated_data):
            approved = validated_data.pop('approved', True)
            user = self._user()
            wiki_translations = instance.wikitranslation_set.all()
            self._update_translations_fields(wiki_translations, approved, user)
            if approved:
                version = instance.create_translated_version(user)
                updated_block = update_edx_block_from_version(version)
                if updated_block:
                    validated_data['applied_translation'] = True
                    validated_data['applied_version'] = version
            
        return super(CourseBlockTranslationSerializer, self).update(instance, validated_data)  

    class Meta:
        model = CourseBlock
        fields = ('block_id', 'block_type', 'course_id', 'approved', 'applied_translation', 'applied_version')
        read_only_fields = ('block_id', 'block_type', 'course_id')

class TranslationVersionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transaltion Version
    """
    class Meta:
        model = TranslationVersion
        fields = ('block_id', 'date', 'data', 'approved_by')
    
    def to_representation(self, value):
        """
        Returns content of a version, data will remain in json format
        """
        content = super(TranslationVersionSerializer, self).to_representation(value)
        content['data'] = value.data
        return content

class CourseBlockVersionSerializer(serializers.ModelSerializer):
    """
    Serializer for course block versions
    """
    class Meta:
        model = CourseBlock
        fields = ('block_id', 'applied_translation', 'applied_version')
        read_only_fields = ('block_id', 'applied_translation')

    def _validate_block_data(self, instance, version):
        """
        Validations to check that requested applied version is valid or not
        """
        if instance.applied_translation and instance.applied_version.id == version.id:
            raise serializers.ValidationError({'applied_version': 'Version is already applied'})
        elif instance.block_id != version.block_id:
            raise serializers.ValidationError({'applied_version': 'Invalid applied version'})
        return True

    def update(self, instance, validated_data):
        """
        Update the version of a block
        """
        version = validated_data['applied_version']

        if self._validate_block_data(instance, version):
            updated_block = update_edx_block_from_version(version)
            if updated_block:
                validated_data['applied_translation'] = True
            else:
                raise serializers.ValidationError("Version is no applied")
        
        return super(CourseBlockVersionSerializer, self).update(instance, validated_data)

class MetaCoursesSerializer(serializers.ModelSerializer):
    """
    Serializer for a translated courses
    """
    class Meta:
        model = CourseTranslation
        fields = ('course_id', 'base_course_id', 'outdated')
        read_only_fields = ('course_id', 'base_course_id', 'outdated')
    
    def to_representation(self, value):
        """
        Returns translated course info
        """
        content = super(MetaCoursesSerializer, self).to_representation(value)
        blocks_count = CourseBlock.objects.filter(course_id=value.course_id, deleted=False).exclude(block_type='course').count()
        blocks_translated = CourseBlock.objects.filter(course_id=value.course_id, deleted=False, translated=True).exclude(block_type='course').count()
        translated_course = get_course_by_id(value.course_id)
        base_course = get_course_by_id(value.base_course_id)
        content.update({
            'course_lang': translated_course.language,
            'course_name': translated_course.display_name,
            'base_course_lang': base_course.language,
            'base_course_name': base_course.display_name,
            'blocks_count': blocks_count,
            'blocks_translated': blocks_translated,
        })
        return content

class MetaCourseTranslationSerializer(serializers.ModelSerializer):
    """
    Serializer for a translated course blocks
    """
    class Meta:
        model = CourseBlock
        fields = ('block_id', 'block_type', 'translated')

    def to_representation(self, value):
        """
        Returns course block info
        """
        content = super(MetaCourseTranslationSerializer, self).to_representation(value)
        wiki_translations = value.wikitranslation_set.all()
        is_parsed_block = False
        base_block_extra_fields= {}
        base_data = {}
        for obj in wiki_translations:
            data_type = obj.source_block_data.data_type
            if WikiTranslation.is_translation_contains_parsed_keys(value.block_type, data_type):
                base_decodings = validate_transaltions(obj.source_block_data.parsed_keys)
                base_decodings = base_decodings if base_decodings else {}
                is_parsed_block = True
                base_data["content"] = base_decodings
            else:
                base_data[data_type] = validate_transaltions(obj.source_block_data.data)
            if not base_block_extra_fields:
                base_block_extra_fields = obj.source_block_data.course_block.extra
        
        page_group_url = ''
        if base_block_extra_fields:
            meta_title = base_block_extra_fields.get('meta_page_title')
            if meta_title:
                course = get_course_by_id(value.course_id)
                page_group_url = WikiMetaClient().get_expected_message_group_redirect_url(meta_title, course.language)     
        
        content.update({
            'base_data': base_data,
            'is_parsed_block': is_parsed_block,
            'group_url': page_group_url,
        })
        return content
