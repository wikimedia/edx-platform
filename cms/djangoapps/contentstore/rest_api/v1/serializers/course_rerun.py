"""
API Serializers for course rerun
"""

from rest_framework import serializers

from django.conf import settings

class CourseRerunSerializer(serializers.Serializer):
    """ Serializer for course rerun """
    allow_unicode_course_id = serializers.BooleanField()
    course_creator_status = serializers.CharField()
    display_name = serializers.CharField()
    number = serializers.CharField()
    org = serializers.CharField()
    run = serializers.CharField()
    is_translated_rerun = serializers.BooleanField()
    language_options = serializers.SerializerMethodField()

    def get_language_options(self, obj):
        """Get language options from translated reruns."""
        return settings.ALL_LANGUAGES

