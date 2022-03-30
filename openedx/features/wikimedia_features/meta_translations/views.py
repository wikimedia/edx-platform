"""
Views for Meta Translations
"""
import json
from logging import getLogger

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock, CourseTranslation
from openedx.features.wikimedia_features.meta_translations.utils import get_recursive_blocks_data, check_and_map_course_blocks

log = getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def course_blocks_mapping(request):
    if request.body:
        course_outline_data = json.loads(request.body)
        course_key_string = course_outline_data["studio_url"].split('/')[2]
        course_key = CourseKey.from_string(course_key_string)

        course = get_course_by_id(course_key)
        course_outline = get_recursive_blocks_data(course, 4, structured=False)
        base_course_key = None
        log.info("Starting course blocks mapping on course_id: ".format(course_key_string))

        # check if course is translated re-run or base-course
        try:
            translation_course_mapping = CourseTranslation.objects.get(course_id=course_key)
            base_course_key = translation_course_mapping.base_course_id
            log.info("Course is a translated re-run version of base course: {}".format(base_course_key))
        except CourseTranslation.DoesNotExist:
            log.info("CourseTranslation object couldn't found - Course is not a translated re-run version.")

        check_and_map_course_blocks(course_outline, course_key, base_course_key)
        return JsonResponse({'success': 'Mapping has been processed successfully.'}, status=200)
    else:
        return JsonResponse({'error':'Invalid request'},status=400)
