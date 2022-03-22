"""
Urls for Meta Translations
"""
from django.conf.urls import include, url

from  openedx.features.wikimedia_features.meta_translations.views import course_blocks_mapping

app_name = 'meta_translations'

urlpatterns = [
    url(
        r'^course_blocks_mapping/$',
        course_blocks_mapping,
        name='course_blocks_mapping'
    )
]
