"""
Urls for Meta Translations
"""
from django.conf.urls import include, url

from  openedx.features.wikimedia_features.meta_translations.views import course_blocks_mapping_view, render_translation_home, update_block_direction_flag

app_name = 'meta_translations'

urlpatterns = [
    url(
        r'^course_blocks_mapping/$',
        course_blocks_mapping_view,
        name='course_blocks_mapping'
    ),
    url(
        r'^direction/$',
        update_block_direction_flag,
        name='direction_flag'
    ),
    url(
        r'^$',
        render_translation_home,
        name='translations_home'
    ),
    url(
        r'^api/v0/',
        include('openedx.features.wikimedia_features.meta_translations.api.v0.urls', namespace='translations_api_v0')
    ),
]
