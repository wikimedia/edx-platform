"""
Views for Meta Translations
"""
import json
from logging import getLogger

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from opaque_keys.edx.keys import CourseKey
from django.conf import settings
from common.djangoapps.edxmako.shortcuts import render_to_response

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock
from openedx.features.wikimedia_features.meta_translations.utils import course_blocks_mapping

log = getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def course_blocks_mapping_view(request):
    if request.body:
        course_outline_data = json.loads(request.body)
        course_key_string = course_outline_data["studio_url"].split('/')[2]
        course_key = CourseKey.from_string(course_key_string)

        if course_blocks_mapping(course_key):
            return JsonResponse({'success': 'Mapping has been processed successfully.'}, status=200)
        else:
            return JsonResponse({'error':'Invalid request'},status=400)
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
