"""
Provider state views needed by pact to setup Provider state for pact verification.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

def test_state():
    print("\n========LIVE TEST STATE==========")
    print("hello from test state!!")
    print("=================================\n")


@csrf_exempt
@require_POST
def provider_state(request):
    """
    Provider state setup view needed by pact verifier.
    """
    state_setup_mapping = {
        'Block data exists': test_state,
    }
    request_body = json.loads(request.body)
    state = request_body.get('state')

    if state in state_setup_mapping:
        print('Setting up provider state for state value: {}'.format(state))
        state_setup_mapping[state]()
    return JsonResponse({'result': state})
