"""
Serializers for Meta-Translations v0 API(s)
"""
from django.utils.translation import ugettext as _
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock, WikiTranslation
from openedx.features.wikimedia_features.meta_translations.utils import get_children_block_ids
from rest_framework import serializers


class WikiTranslationSerializer(serializers.ModelSerializer):
    """
    Serializer for wikitranslation
    """
    id = serializers.IntegerField()
    class Meta:
        model = WikiTranslation
        fields = ('id', 'target_block', 'translation', 'applied', 'last_fetched', 'revision', 'approved_by')
        read_only_fields = ('id', 'target_block', 'last_fetched', 'revision', 'approved_by')


class CourseBlockSerializer(serializers.ModelSerializer):
    """
    Serializer for courseblock
    """
    wiki_translations = WikiTranslationSerializer(source='wikitranslation_set', many=True, required=False)
    apply_all = serializers.BooleanField(required=False, write_only=True)
    applied = serializers.BooleanField(required=True, write_only=True)

    def to_representation(self, value):
        """
        Add applied field in block. True if all the translations are applied else false
        """
        data = super(CourseBlockSerializer, self).to_representation(value)
        data['applied'] = all([translation['applied'] for translation in data['wiki_translations']])
        return data

    def to_internal_value(self, data):
        """
        If data cantains wiki_translations, add the applied field in all
        """
        if 'wiki_translations' in data:
            translations_data = []
            for translation in data['wiki_translations']:
                new_trans = {}
                new_trans.update(translation)
                new_trans.update({'applied': data['applied']})
                translations_data.append(new_trans)
            data['wiki_translations'] = translations_data
        return data

    def validate(self, data):
        """
        validations for serializer
        """
        if 'apply_all' in data and 'wiki_translations' in data:
            if data['apply_all']:
                raise serializers.ValidationError("apply_all can't be 'true' with wiki_translations argument")
        return data
    
    def _user(self):
        """
        Get user from request
        """
        request = self.context.get('request', None)
        if request:
            return request.user
    
    def _validate_translations(self, instances, validated_data):
        """
        A custom validation that checks wiki_traslations and course block instances
        wiki_translations must include all the instances of the block
        """
        instances_ids = set([instance.id for instance in instances])
        data_ids = set([data['id'] for data in validated_data])
        if instances_ids != data_ids:
            raise serializers.ValidationError("wiki_translations didn't matched with block translations")
    
    def _update_translations(self, instances, validated_data):
        """
        Update WikiTranslation instances with validated_
        """
    
    def _update_translations_fields(self, instances, applied, user):
        """
        Update WikiTranslation instances with applied and user fields
        Note: It'll apply same fields to all the instances
        """
        for instance in instances:
            if applied:
                instance.applied = applied
            if user:
                instance.user = user
            instance.save()

    def update(self, instance, validated_data):
        """
        Update method override
        if 'apply_all' is true
            It applies 'applied' status to the block and their children
        if 'wiki_translations'
            First it validates translations in wiki_translations
            Then it applies those translations to database
        Otherwise It only update 'applied' status to current block wiki_translations
        At last it calls the default update methord
        """
        applied = validated_data.pop('applied')
        user = self._user()
        if validated_data.get('apply_all'):
            validated_data.pop('apply_all')
            block_ids = get_children_block_ids(instance.block_id)
            wiki_translations = WikiTranslation.objects.filter(target_block__block_id__in=block_ids)
            self._update_translations_fields(wiki_translations, applied, user)
        else:
            wiki_translations = WikiTranslation.objects.filter(target_block=instance)
            if 'wiki_translations' in validated_data:
                block_translations = validated_data.pop('wiki_translations')
                self._validate_translations(wiki_translations, block_translations)
                for block_translation in block_translations:
                    id = block_translation.pop('id')
                    instance = wiki_translations.get(id=id)
                    instance.approved_by = user
                    instance.applied = block_translation['applied']
                    if 'translation' in block_translation:
                        instance.translation = block_translation['translation']
                    instance.save()      
            else:
                self._update_translations_fields(wiki_translations, applied, user)

        return super(CourseBlockSerializer, self).update(instance, validated_data)

    def create(self, validated_data):
        """
        Call default create method after removing extra fields.
        """
        extra_fields = ['wiki_translations', 'apply_all', 'applied']
        for field in extra_fields:
            if field in validated_data:
                validated_data.pop(field)
        return super(CourseBlockSerializer, self).create(validated_data)
    
    class Meta:
        model = CourseBlock
        fields = ('block_id', 'block_type', 'course_id', 'wiki_translations', 'apply_all', 'applied')
        read_only_fields = ('block_id', 'block_type', 'course_id')
