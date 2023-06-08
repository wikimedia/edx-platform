"""
Urls for Messenger v0 API(s)
"""
from django.conf import settings
from django.conf.urls import url

from openedx.features.wikimedia_features.wikimedia_general.api.v0.views import (
    RetrieveWikiMetaData, get_courses_to_study_next, RetrieveLMSTabs,
)

app_name = 'general_api_v0'

urlpatterns = [
    url(
        fr'^wiki_metadata/{settings.COURSE_KEY_PATTERN}',
        RetrieveWikiMetaData.as_view(),
        name='course_font',
    ),
    url(
        r'^courses/study_next',
        get_courses_to_study_next,
        name='study_next',
    ),
    url(
        r'lms_tabs',
        RetrieveLMSTabs.as_view(),
        name='retrieve_lms_tabs'
    ),
]
