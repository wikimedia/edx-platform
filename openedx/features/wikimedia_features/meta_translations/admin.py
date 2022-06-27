"""
Admin registration for Messenger.
"""
from config_models.admin import ConfigurationModelAdmin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openedx.features.wikimedia_features.meta_translations.models import (
   CourseBlock, CourseBlockData, CourseTranslation, TranslationVersion, WikiTranslation, MetaTranslationConfiguration
)


class CourseBlockAdmin(admin.ModelAdmin):
    """
    Admin config clearesult credit providers.
    """
    list_display  = (
        "block_id", "parent_id", "block_type", "course_id", "direction_flag", "lang",
        "data", "applied_translation", "applied_version", "deleted"
    )
    search_fields = ("block_id", "course_id",)
    list_filter = ('block_type', 'direction_flag', 'applied_translation', 'deleted')

    def data(self, obj):
        data = {}
        for block_data in obj.courseblockdata_set.all():
            data[block_data.data_type] = block_data.data[:30]

        if not data:
            data = "translated version"

        return data

class CourseBlockDataAdmin(admin.ModelAdmin):
    """
    Admin config for clearesult credits offered by the courses.
    """
    list_display  = ("course_block", "data_type", "data", "parsed_keys", "should_send",)
    search_fields = ("course_block__block_id", "course_block__course_id", "data_type")

    def should_send(self, obj):
        return obj.content_updated or obj.mapping_updated

    list_filter = ("course_block__block_type", "data_type", "content_updated", "mapping_updated")

class CourseTranslationAdmin(admin.ModelAdmin):
    """
    Admin config for clearesult credits offered by the courses.
    """
    list_display  = [f.name for f in CourseTranslation._meta.fields]
    search_fields = ("course_id", "base_course_id",)

class WikiTranslationAdmin(admin.ModelAdmin):
    """
    Admin config for clearesult credits offered by the courses.
    """
    list_display  = [f.name for f in WikiTranslation._meta.fields]
    search_fields = ("target_block__block_id", "target_block__course_id", "source_block_data__data_type",)
    list_filter = ("target_block__block_type", "source_block_data__data_type", "approved",)

    def translation(self, obj):
        if obj.translation:
            return obj.translation[:30]

class TranslationVersionAdmin(admin.ModelAdmin):
    """
    Admin config for clearesult credits offered by the courses.
    """
    list_display = [f.name for f in TranslationVersion._meta.fields]
    search_fields = ("block_id", "date")


admin.site.register(CourseBlock, CourseBlockAdmin)
admin.site.register(CourseBlockData, CourseBlockDataAdmin)
admin.site.register(CourseTranslation, CourseTranslationAdmin)
admin.site.register(WikiTranslation, WikiTranslationAdmin)
admin.site.register(TranslationVersion, TranslationVersionAdmin)
admin.site.register(MetaTranslationConfiguration, ConfigurationModelAdmin)
