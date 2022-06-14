"""
Serializers for Meta-Translations v0 API(s)
"""
from django.utils.translation import ugettext as _

from common.lib.xmodule.xmodule.modulestore.django import modulestore
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock, TranslationVersion
from openedx.features.wikimedia_features.meta_translations.wiki_components import COMPONENTS_CLASS_MAPPING
from rest_framework import serializers

class CourseBlockTranslationSerializer(serializers.ModelSerializer):
    """
    Serializer for a courseblock
    """
    approved = serializers.BooleanField(required=False, write_only=True, default=True)

    def to_representation(self, instance):
        """
        Add approved field in block. True if all the translations are approved else false
        We also need latest version that is approved
        """
        data = super(CourseBlockTranslationSerializer, self).to_representation(instance)
        data['approved'] = instance.is_translations_approved()
        data['latest_version'] = instance.get_latest_version()
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
        approved = validated_data.pop('approved', True)
        user = self._user()
        wiki_translations = instance.wikitranslation_set.all()
        self._update_translations_fields(wiki_translations, approved, user)
        if approved:
            instance.create_translated_version(user)
        
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
            data = version.data
            block_location = version.block_id
            block =  modulestore().get_item(block_location)
            updated_block = COMPONENTS_CLASS_MAPPING[block_location.block_type]().update(block, data)
            
            if updated_block:
                validated_data['applied_translation'] = True
            else:
                raise serializers.ValidationError("Version is no applied")
        
        return super(CourseBlockVersionSerializer, self).update(instance, validated_data)
