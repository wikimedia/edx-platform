"""
Forum urls for the django_comment_client.
"""
from django.conf.urls import url, patterns

from .views import WikimediaProgressFragmentView

urlpatterns = patterns(
    'wikimedia_general.views',
    url(
        r'progress_fragment_view$',
        WikimediaProgressFragmentView.as_view(),
        name='progress_fragment_view'
    ),
)
