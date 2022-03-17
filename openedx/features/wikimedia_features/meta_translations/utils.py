"""
Files containes helping functions assosiated with meta_translations
"""

from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation


def set_course_translation(course_key, source_key):
    """
    updete course translation table
    """
    course_id = str(course_key)
    base_course_id = str(source_key)
    CourseTranslation.objects.create(course_id = course_id, base_course_id = base_course_id)
