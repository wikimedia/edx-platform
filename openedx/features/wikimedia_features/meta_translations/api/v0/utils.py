"""
Helping functions to get data of a course
"""

import json
from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField
from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation
from xmodule.video_module.transcripts_utils import get_video_transcript_content

def get_html_components_data(block):
    return {
        "display_name": block.display_name,
        "content": block.data
    }

def get_video_components_data(block):
    data = get_video_transcript_content(block.edx_video_id, block.transcript_language)
    json_content = json.loads(data['content'].decode("utf-8"))
    return {
        "display_name": block.display_name,
        "transcript": json_content['text']
    }

def get_outline_components_data(block):
    return {
        'display_name': block.display_name
    }

def get_course_component_data(block):
    return {
        'display_name': block.display_name,
    }

COMPONENTS_FUNCTION_MAPPING = {
    'course': get_course_component_data,
    'chapter': get_outline_components_data,
    'sequential': get_outline_components_data,
    'vertical': get_outline_components_data,
    'html': get_html_components_data,
    'problem': get_html_components_data,
    'video': get_video_components_data
}

def get_block_data(block):
    return {
        'usage_key': str(block.scope_ids.usage_id),
        'category': block.category,
        'data': COMPONENTS_FUNCTION_MAPPING[block.category](block)
    }

def get_outline_structured(block, depth=3):
    if depth == 0 or not hasattr(block, 'children'):
        return get_block_data(block)
    data = get_block_data(block)
    data['children'] = []
    for child in block.get_children():
        data['children'].append(get_outline_structured(child, depth - 1))
    return data

def get_outline_unstructured(block, depth=3):
    if depth == 0 or not hasattr(block, 'children'):
        return [get_block_data(block)]
    data = [get_block_data(block)]
    for child in block.get_children():
        data.extend(get_outline_unstructured(child, depth - 1))
    return data

def get_outline_course_to_sections(course):
    return get_outline_structured(course, 2)

def get_outline_subsections_to_component(sub_section):
    return get_outline_structured(sub_section)

def get_course_version_object(course_key):
    course = get_course_by_id(course_key)
    version_obj = {
        'id': str(course.course_id),
        'title': course.display_name,
        'language': course.language
        }
    return str(course.course_id), version_obj

def get_courses_of_base_course(base_course_id):
    course_varsions = CourseTranslation.objects.filter(base_course_id = base_course_id)
    translated_courses = [get_course_version_object(course_version.course_id) for course_version in course_varsions]
    return dict(translated_courses)

def mapping_blocks(course_id, base_course_id):
    course_key = CourseKeyField.from_string(course_id)
    base_course_key = CourseKeyField.from_string(base_course_id)
    
    course = get_course_by_id(course_key)
    base_course = get_course_by_id(base_course_key)

    course_blocks = get_outline_unstructured(course, 4)
    base_course_blocks = get_outline_unstructured(base_course, 4)
    
    # for course_block, base_course_block in zip(course_block, base_course_block):


