"""
Views for Meta Translations
"""
import json
from logging import getLogger

from django.core import management
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from opaque_keys.edx.keys import CourseKey, UsageKey
from django.conf import settings
from common.djangoapps.edxmako.shortcuts import render_to_response
from django.utils.translation import ugettext_lazy as _

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import CourseBlock
from openedx.features.wikimedia_features.meta_translations.mapping.utils import course_blocks_mapping
from openedx.features.wikimedia_features.meta_translations.mapping.exceptions import MultipleObjectsFoundInMappingCreation

log = getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def course_blocks_mapping_view(request):
    if request.body:
        course_outline_data = json.loads(request.body)
        course_key_string = course_outline_data["studio_url"].split('/')[2]
        course_key = CourseKey.from_string(course_key_string)

        try:
            if course_blocks_mapping(course_key):
                return JsonResponse({'success': 'Mapping has been processed successfully.'}, status=200)
            else:
                return JsonResponse({'error':'Invalid request'},status=400)
        except MultipleObjectsFoundInMappingCreation as ex:
            error_msg = ex.message
            if ex.block_id:
                error_msg = "Unable to process block_id: {}. {}".format(ex.block_id, ex.message)
            return JsonResponse({'error': error_msg},status=400)
    else:
        return JsonResponse({'error':'Invalid request'},status=400)


@login_required
@require_http_methods(["POST"])
def course_blocks_api_send_fetch(request):
    """
    Trigers meta api send translations command on given course_id
    """
    if request.body:
        params = json.loads(request.body)
        action = params.get('action')
        if action in ['send', 'fetch']:
            if action == 'send':
                output = management.call_command(
                    'sync_untranslated_strings_to_meta_from_edx',
                    commit=True)
            else:
                output = management.call_command(
                    'sync_translated_strings_to_edx_from_meta',
                    commit=True
                )
            return JsonResponse({'success': 'API command has been triggered successfully.'}, status=200)
        else:
            return JsonResponse({'error':'Invalid params in request.'},status=400)
    else:
        return JsonResponse({'error':'Invalid request'},status=400)


@login_required
def render_translation_home(request):
    meta_data = {
        'expend_outline': _('Expend Outline'),
        'collapse_outline': _('Collapse Outline'),
        'select_base_course': _('Select Base Course'),
        'select_rerun_course': _('Select Rerun Course'),
        'messages': {
                'course_error': _('No Translated Course Found!'),
                'translation_error': _('No Translations Found!, Please apply mapping.')
            },
        'filter_my_courses': _('Filter My Courses'),
        'approve_button': {
            'label': _('APPROVE'),
            'disabled': _('Translation is Disabled'),
            'incomplete': _('Incomplete Translation'),
            'approve': _('Approve'),
            'approved': _('Approved'),
            'error': _('Unable to approve this time, Please try again later.'),
            'success': _("Congratulations! The translation is approved. It's also applied automatically to the Course Block")
        },
        'apply_button': {
            'label': _('APPLY'),
            'disabled': _('Translation is Disabled'),
            'applied': _('Applied'),
            'apply': _('Apply'),
            'error': _('Unable to apply this time, Please try again later.'),
            'success': _('Congratulations! The translation is applied to the Course Block')
        },
        'applied_badge': {
            'label': _('APPLIED')
        },
        'approve_all_button': {
            'label': _('APPROVE ALL'),
            'not_found': _('No pending translations to be approved'),
            'error': _('Unable to approve this time, Please try again later.'),
            'success': _("Congratulations! Translations are approved. They're also applied automatically to the Course Blocks"),
        },
        'options_tags': {
            'pending': _('pending translation'),
            'recent': _('recent'),
            'applied': _('applied'),
            'other': _('other'),
        },
        'errors': {
            'fetch_transaltion': _('Unable to fetch translation this time, Please try again later.'),
            'fetch_courses': _('Unable to load Courses.'),
            'fetch_outline': _('Unable to load Course Outline.'),
            'fetch_content': _('Unable to load content.'),
        }
    }
    return render_to_response('translations.html', {
        'uses_bootstrap': True,
        'login_user_username': request.user.username,
        'language_options': dict(settings.ALL_LANGUAGES),
        'meta_data': meta_data,
        'is_admin': request.user.is_superuser
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

def render_discover_courses(request, course_key=None):
    meta_data = {
        'filters': _('Filters'),
        'from_lang': _('From Language'),
        'to_lang': _('To Language'),
        'block_type': _('Block Type'),
        'translation': _('Translation'),
        'course_name': _('Course Name'),
        'translated_course_name': _('Translated Course Name'),
        'serch_course_by_name': _('Search Course By Name'),
        'hrs_ago': _('Hrs Ago'),
        'not_applicable': _('N/A'),
        'translated': _('Translated'),
        'badges': {
            'last_updated': _('Last Updated:'),
            'translated': _('Translated:'),
        },
        'info': {
            'blocks_not_found': _('No course blocks found'),
            'courses_not_found': _('No courses found')
        },
        'buttons': {
            'load_more': _('Load More'),
            'apply': _('Apply'),
        },
        'blocks_filter': {
            'section_header': _('Section Header'),
            'html': _('HTML'),
            'video': _('Video'),
            'problem': _('Problem'),
        },
        'translation_filter': {
            'translated': _('Translated'),
            'untranslated': _('Untranslated'),
        },
        'errors': {
            'fetch_blocks': _('Unable to load course blocks'),
            'fetch_course': _('Unable to load a course'),
            'fetch_courses': _('Unable to load courses'),
        }
    }
    return render_to_response('discover_courses.html', {
        'uses_bootstrap': True,
        'language_options': dict(settings.ALL_LANGUAGES),
        'meta_data': meta_data,
    })
