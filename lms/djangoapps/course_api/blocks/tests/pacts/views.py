"""
Provider state views needed by pact to setup Provider state for pact verification.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


class TestState:
    def __init__(self):
        pass


@csrf_exempt
@require_POST
def provider_state(request):
    """
    Provider state setup view needed by pact verifier.
    """
    state_setup_mapping = {
        'Blocks data exists for course_id edX/DemoX/course/Demo_Course': TestState,
    }
    request_body = json.loads(request.body)
    state = request_body.get('state')

    if state in state_setup_mapping:
        print('Setting up provider state for state value: {}'.format(state))
        state_setup_mapping[state]()
    return JsonResponse({'result': state})
