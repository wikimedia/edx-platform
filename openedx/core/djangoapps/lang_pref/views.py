"""
Language Preference Views
"""


import json

from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import LANGUAGE_SESSION_KEY
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from openedx.core.djangoapps.lang_pref import LANGUAGE_KEY
from openedx.core.djangoapps.lang_pref.helpers import set_language_cookie
from openedx.core.djangoapps.lang_pref.api import header_language_selector_is_enabled, released_languages

@ensure_csrf_cookie
def update_session_language(request):
    """
    Update the language session key.
    """
    response = HttpResponse(200)
    if request.method == 'PATCH':
        data = json.loads(request.body.decode('utf8'))
        language = data.get(LANGUAGE_KEY, settings.LANGUAGE_CODE)
        if request.session.get(LANGUAGE_SESSION_KEY, None) != language:
            request.session[LANGUAGE_SESSION_KEY] = str(language)
        set_language_cookie(request, response, language)
    return response


@api_view(['GET'])
@login_required
def get_released_languages(request):
    """
    An endpoint to enable language selector drop down in the MFEs.
    This is used to get the list of released languages.
    """
    response =  {
        'released_languages': released_languages(),
    }
    return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
@login_required
def get_language_selector_is_enabled(request):
    """
    Get whether the language selector is enabled or not.
    """
    language_selector_is_enabled = header_language_selector_is_enabled()
    response =  {
        'language_selector_is_enabled': language_selector_is_enabled,
    }
    return Response(response, status=status.HTTP_200_OK)
