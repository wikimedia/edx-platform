"""
Forum urls for the django_comment_client.
"""
from django.conf.urls import url, include

app_name = 'wikimedia_general'

urlpatterns = [
    url(
        r'^api/v0/',
        include('openedx.features.wikimedia_features.wikimedia_general.api.v0.urls', namespace='general_api_v0')
    ),
]
