from django.conf.urls import url, include

from .views import WikimediaProgressFragmentView

app_name = 'progress_tab'

urlpatterns = [
    url(
        r'progress_fragment_view$',
        WikimediaProgressFragmentView.as_view(),
        name='progress_fragment_view'
    ),
]
