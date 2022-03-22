"""
Urls for Meta Translations
"""
from django.conf.urls import include, url

from openedx.features.wikimedia_features.meta_translations.views import render_translation_home

app_name = 'meta_translations'

urlpatterns = [
    url(
        r'^(?P<course_id>.+)$',
        render_translation_home,
        name='translations_home'
    ),
    url(
        r'^api/v0/',
        include('openedx.features.wikimedia_features.meta_translations.api.v0.urls', namespace='translations_api_v0')
    ),
]
