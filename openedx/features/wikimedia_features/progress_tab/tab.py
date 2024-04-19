from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_noop

from lms.djangoapps.courseware.tabs import EnrolledTab
from xmodule.tabs import TabFragmentViewMixin


class WikimediaProgressTab(TabFragmentViewMixin, EnrolledTab):
    type = 'wikimedia_progress_tab'
    title = ugettext_noop('Progress')
    priority = None
    fragment_view_name = 'openedx.features.wikimedia_features.progress_tab.views.WikimediaProgressFragmentView'
    is_hideable = False
    is_default = True
    body_class = 'wikimedia_progress'

    @classmethod
    def is_enabled(cls, course, user=None):
        if not super().is_enabled(course, user=user):
            return False
        return True
