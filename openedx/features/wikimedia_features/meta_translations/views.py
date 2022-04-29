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
from django.conf import settings
from common.djangoapps.edxmako.shortcuts import render_to_response

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

@login_required
def render_translation_home(request):
    return render_to_response('translations.html', {
        'uses_bootstrap': True,
        'login_user_username': request.user.username,
        'language_options': dict(settings.ALL_LANGUAGES),
    })

@login_required
@require_http_methods(["POST"])
def update_block_direction_flag(request):
    """
    Update Direction Flag in Course Block
    Request:
    {
        locator: <course_block_key>,
        destination_flag: <boolean>
    }
    """
    if request.body:
        block_fields_data = json.loads(request.body)
        locator = block_fields_data['locator']
        destination_flag = block_fields_data['destination_flag']
        course_block = CourseBlock.objects.get(block_id=locator)
        if (destination_flag and course_block.is_source()) or course_block.is_destination():
            course = get_course_by_id(course_block.course_id)
            
            if destination_flag:
                course_block = course_block.update_flag_to_destination(course.language)
            else:
                course_block = course_block.update_flag_to_source(course.language)
            
            if course_block:
                response = {
                    'success': 'Block status is updated',
                    'destination_flag': course_block.is_destination(),
                }
                return JsonResponse(response, status=200)
            
            error_message = 'No Mapping found. Please click Mapping Button on outline page to update Mappings'
            return JsonResponse({'error': error_message}, status=405)
    
    return JsonResponse({'error':'Invalid request'}, status=400)
