"""
Permissions for Meta-Translations v0 API(s)
"""
from rest_framework.permissions import BasePermission

from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation

class DestinationCourseOnly(BasePermission):
    def has_permission(self, request, view):
        """
        Only allow destination courses
        """
        course_id = view.kwargs.get('course_key', None)
        return CourseTranslation.objects.filter(course_id=course_id).exists()
    
    def has_object_permission(self, request, view, obj):
        """
        Only allow destination blocks
        """
        if obj.is_source():
            return False
        return True
