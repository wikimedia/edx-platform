"""
Provider state views needed by pact to setup Provider state for pact verification.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.tests.django_utils import ModuleStoreIsolationMixin
from xmodule.modulestore.tests.factories import CourseFactory


class TestState(ModuleStoreIsolationMixin):
    """ Test State Setup """
    def __init__(self):
        try:
            self.end_modulestore_isolation()
        except IndexError:
            pass
        self.start_modulestore_isolation()

        self.course_key = CourseKey.from_string('course-v1:edX+DemoX+Demo_Course')
        self.course = CourseFactory.create(
            org=self.course_key.org,
            course=self.course_key.course,
            run=self.course_key.run,
            display_name="Demonstration Course",
            modulestore=self.store
        )


class TestState2(ModuleStoreIsolationMixin):
    """ Test State Setup """

    def __init__(self):
        try:
            self.end_modulestore_isolation()
        except IndexError:
            pass
        self.start_modulestore_isolation()

        self.course_key = CourseKey.from_string('course-v1:edX+DemoY+Demo_Course')
        self.course = CourseFactory.create(
            org=self.course_key.org,
            course=self.course_key.course,
            run=self.course_key.run,
            display_name="Demonstration Course",
            modulestore=self.store
        )


@csrf_exempt
@require_POST
def provider_state(request):
    """
    Provider state setup view needed by pact verifier.
    """
    state_setup_mapping = {
        'Blocks data exists for course_id edX/DemoX/course/Demo_Course': TestState,
        'Blocks data exists for course_id edX/DemoX/course/Demo_Course - Duplicate': TestState,
        'Blocks data exists for course_id edX/DemoY/course/Demo_Course': TestState2,
    }
    request_body = json.loads(request.body)
    state = request_body.get('state')

    if state in state_setup_mapping:
        print('Setting up provider state for state value: {}'.format(state))
        state_setup_mapping[state]()

    return JsonResponse({'result': state})
