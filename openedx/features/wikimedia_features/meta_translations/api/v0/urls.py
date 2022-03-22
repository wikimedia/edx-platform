"""
Urls for Messenger v0 API(s)
"""
from django.conf.urls import url
from openedx.features.wikimedia_features.meta_translations.api.v0.views import GetSubSectionContent, GetTranslationOutlineStructure


app_name = 'translations_api_v0'


urlpatterns = [
    url(
        r'^outline/(?P<course_key_string>.+)$',
        GetTranslationOutlineStructure.as_view(),
        name='outline',
    ),
    url(
        r'^subsection/(?P<subsection_id>.+)$',
        GetSubSectionContent.as_view(),
        name='subsection',
    ),
]
