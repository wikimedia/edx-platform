"""
Helping functions to get data of a course
"""

import json
from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation
from xmodule.video_module.transcripts_utils import get_video_transcript_content
import string
import random

def get_random_string(N=16):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))

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

def get_module_data(block):
    return {
        'display_name': block.display_name
    }

COMPONENTS_FUNCTION_MAPPING = {
    'course': get_module_data,
    'chapter': get_module_data,
    'sequential': get_module_data,
    'vertical': get_module_data,
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

def get_outline_structured_with_keys(block, depth=3):
    if depth == 0 or not hasattr(block, 'children'):
        return { get_random_string() : get_block_data(block) }
    random_key = get_random_string()
    data = {  random_key : get_block_data(block) }
    data[random_key]['children'] = {}
    for child in block.get_children():
        data[random_key]['children'].update(get_outline_structured_with_keys(child, depth - 1))
    return data

def get_outline_structured_with_keys_testing(base_block, block, depth=3):
    
    if depth == 0 or not hasattr(block, 'children'):
        random_key = get_random_string()
        base_data = { random_key: get_block_data(base_block) }
        data = { random_key: get_block_data(block) }
        return base_data, data
    
    random_key = get_random_string()
    base_data = { random_key: get_block_data(base_block)}
    data = {  random_key: get_block_data(block) }

    data[random_key]['children'] = {}
    base_data[random_key]['children'] = {}

    for base_child, child in zip(base_block.get_children(), block.get_children()):
        base_outline, outline = get_outline_structured_with_keys_testing(base_child, child, depth - 1)
        base_data[random_key]['children'].update(base_outline)
        data[random_key]['children'].update(outline)

    return base_data, data

def get_outline_course_to_sections_testing(base_course, course):
    return get_outline_structured_with_keys_testing(base_course, course, 2)

def get_outline_subsections_to_component_testing(base_subsection, sub_section):
    return get_outline_structured_with_keys_testing(base_subsection, sub_section)

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

