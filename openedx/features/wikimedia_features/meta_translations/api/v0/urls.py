"""
Urls for Messenger v0 API(s)
"""
from django.conf.urls import url
from openedx.features.wikimedia_features.meta_translations.api.v0.views import GetCoursesVersionInfo, GetSubSectionContent, GetTranslationOutlineStructure


app_name = 'translations_api_v0'


urlpatterns = [
    url(
        r'^outline/(?P<course_key>.+)/(?P<base_course_key>.+)$',
        GetTranslationOutlineStructure.as_view(),
        name='outline',
    ),
    # url(
    #     r'^outline$',
    #     GetTranslationOutlineStructure.as_view(),
    #     name='outline',
    # ),
    url(
        r'^subsection/(?P<subsection_key>.+)/(?P<base_subsection_key>.+)$',
        GetSubSectionContent.as_view(),
        name='subsection',
    ),
    url(
        r'^versions$',
        GetCoursesVersionInfo.as_view(),
        name='subsection',
    ),
]
