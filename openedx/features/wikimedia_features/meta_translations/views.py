"""
Views for Messenger
"""
from django.contrib.auth.decorators import login_required
from django.conf import settings
from common.djangoapps.edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user
from openedx.features.wikimedia_features.meta_translations.utils import get_base_course_id


@login_required
def render_translation_home(request):
    return render_to_response('translations.html', {
        'uses_bootstrap': True,
        'login_user_username': request.user.username,
        'language_options': dict(settings.ALL_LANGUAGES),
    })
