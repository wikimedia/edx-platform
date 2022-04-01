"""
Admin registration for Messenger.
"""
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openedx.features.wikimedia_features.meta_translations.models import (
   CourseBlock, CourseBlockData, CourseTranslation
)


class CourseBlockAdmin(admin.ModelAdmin):
    """
    Admin config clearesult credit providers.
    """
    list_display  = [f.name for f in CourseBlock._meta.fields]



class CourseBlockDataAdmin(admin.ModelAdmin):
    """
    Admin config for clearesult credits offered by the courses.
    """
    list_display  = [f.name for f in CourseBlockData._meta.fields]


class CourseTranslationAdmin(admin.ModelAdmin):
    """
    Admin config for clearesult credits offered by the courses.
    """
    list_display  = [f.name for f in CourseTranslation._meta.fields]


admin.site.register(CourseBlock, CourseBlockAdmin)
admin.site.register(CourseBlockData, CourseBlockDataAdmin)
admin.site.register(CourseTranslation, CourseTranslationAdmin)
