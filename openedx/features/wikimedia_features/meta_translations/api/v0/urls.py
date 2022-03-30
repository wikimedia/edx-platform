"""
Urls for Messenger v0 API(s)
"""
from django.conf.urls import url
from openedx.features.wikimedia_features.meta_translations.api.v0.views import GetCoursesVersionInfo, GetTranslationOutlineStructure, GetVerticalComponentContent


app_name = 'translations_api_v0'


urlpatterns = [
    url(
        r'^outline/(?P<course_key>.+)/(?P<base_course_key>.+)$',
        GetTranslationOutlineStructure.as_view(),
        name='outline',
    ),
    url(
        r'^components/(?P<unit_key>.*?)/(?P<base_unit_key>.*?)$',
        GetVerticalComponentContent.as_view(),
        name='components',
    ),
    url(
        r'^versions$',
        GetCoursesVersionInfo.as_view(),
        name='versions',
    ),
]
