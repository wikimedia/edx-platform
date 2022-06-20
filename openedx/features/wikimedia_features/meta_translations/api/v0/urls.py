"""
Urls for Messenger v0 API(s)
"""
from django.conf.urls import url

from openedx.features.wikimedia_features.meta_translations.api.v0.views import (
    ApproveAPIView, CouseBlockVersionUpdateView, GetCoursesVersionInfo,
    GetTranslationOutlineStructure, GetVerticalComponentContent, TranslatedVersionRetrieveAPIView
)

app_name = 'translations_api_v0'

urlpatterns = [
    url(
        r'^outline/(?P<course_key>.+)$',
        GetTranslationOutlineStructure.as_view(),
        name='outline',
    ),
    url(
        r'^components/(?P<unit_key>.*?)$',
        GetVerticalComponentContent.as_view(),
        name='components',
    ),
    url(
        r'^versions$',
        GetCoursesVersionInfo.as_view(),
        name='versions',
    ),
    url(
         r'^approve_translations/$',
        ApproveAPIView.as_view(),
        name='approve-translations'
    ),
    url(
        r'^translated_versions/(?P<pk>\d+)/$',
        TranslatedVersionRetrieveAPIView.as_view(),
        name='translated_versions'
    ),
    url(
        r'^apply_translated_version/(?P<block_id>.*?)/$',
        CouseBlockVersionUpdateView.as_view(),
        name='course_block_version'
    ),
]
