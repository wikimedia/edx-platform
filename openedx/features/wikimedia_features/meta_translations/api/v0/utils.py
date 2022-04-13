"""
Helping functions used in meta translation apis
"""
import json
import string
import random

from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation, WikiTranslation
from openedx.features.wikimedia_features.meta_translations.utils import COMPONENTS_FUNCTION_MAPPING


def validate_string(data):
    """
    Function that validates data of type display_name and content
    Returns:
        string: Empty if None else data
    """
    if data == None:
        return ''
    return data

def validate_list_data(data):
    """
    Function that validate data of type transcript
    Returns:
        list: Empty if None else list of strings
    """
    if data == None:
        return []
    return json.loads(data)

BLOCK_DATA_TYPES_DATA = {
    'content': validate_string,
    'display_name': validate_string,
    'transcript': validate_list_data,
}

def get_random_string(N=16):
    """
    Arguments:
        N: Integer, length of random string
    Returns:
        string: A random string consisting of numbers and uppercase digits
                Default length: 16
    """
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))

def get_block_data_from_table(block, wiki_objects):
    """
    Function that return a data block of a course and it's base course.
    All the values are extracted from Meta Translations Tables
    (
        {
            "usage_key":"block_component_usage_id",
            "category":"problem",
            "data_block_ids: {
                "display_name": 1,
                "content": 10
            },
            "data":{
                "display_name":"Problem 1",
                "content":"<problem>This is the problem....<problem>"
            }
        },
        {
            "usage_key":"base_block_component_usage_id",
            "category":"problem",
            "data":{
                "display_name":"",
                "content":""
            }
        }
    )
    Arguments:
        block: course-outline block
        wiki-objects: filter-type WikiTranslation object
    Return:
        block_data: dict(usage_key, category, data_block_ids, data)
        translated_block_data: dict(usage_key, category, data)
    """
    if block.category in COMPONENTS_FUNCTION_MAPPING:
        usage_key = str(block.scope_ids.usage_id)
        block_fields = {}
        base_block_fields = {}
        block_fields_ids = {}
        wiki_objects = wiki_objects.filter(target_block__block_id=usage_key)
        base_usage_key = ''
        for obj in wiki_objects:
            data_type = obj.source_block_data.data_type
            block_fields_ids[data_type] = obj.id
            block_fields[data_type] = BLOCK_DATA_TYPES_DATA[data_type](obj.translation)
            base_block_fields[data_type] = BLOCK_DATA_TYPES_DATA[data_type](obj.source_block_data.data)
            base_usage_key = str(obj.source_block_data.course_block.block_id)
        
        course_block_data = {
            'usage_key': usage_key,
            'category': block.category,
            'data_block_ids': block_fields_ids,
            'data': block_fields,
        }
        base_course_block_data = {
            'usage_key': base_usage_key,
            'category': block.category,
            'data': base_block_fields
        }
        return course_block_data, base_course_block_data
    return {}, {}

def get_recursive_blocks_data_from_table(block, wiki_objects, depth=4):
    """
    Retrieve data from blocks of course and base course with random identification key.
    {
        ABCDASDAGSEEESD0:{
            "7VLKTTPX1ZUJI8KA":{
                "usage_key":"block_component_usage_id",
                "category":"problem",
                "data_block_ids: {
                    "display_name": 1,
                    "content": 10
                },
                "data":{
                    "display_name":"Problem 1",
                    "content":""
                }
            },
            "B36BXKA90A56Y5QI":{
                "usage_key":"block_component_usage_id",
                "category":"html",
                "data_block_ids: {
                    "display_name": 1,
                    "content": 10
                },
                "data": {
                    "display_name":"Html Text",
                    "content":"<h1>Hello World<h1/>"
                }
            },
        },

        ABCDASDAGSEEESD0:{
            "7VLKTTPX1ZUJI8KA":{
                "usage_key":"base_block_component_usage_id",
                "category":"problem",
                "data": {
                    "display_name":"SDAFADASD 1",
                    "content":""
                }
            },
            "B36BXKA90A56Y5QI":{
                "usage_key":"base_block_component_usage_id",
                "category":"html",
                "data": {
                    "display_name":"HERA TESD",
                    "content":""
                }
            },
        }
    }
    Arguments:
        block: course-outline block
        wiki-objects: filter-type WikiTranslation object
    Return:
        course-outline: structured dict
        base-course-outline: structed dict
    A random key is generated to identify block in course-outline and
    corrensponding block in base-course-outline
    """
    if depth == 0 or not hasattr(block, 'children'):
        random_key = get_random_string()
        data, base_data = get_block_data_from_table(block, wiki_objects)
        data_map, base_data_map = {}, {}
        if data and base_data:
            data_map[random_key] = data
            base_data_map[random_key] = base_data        
        return data_map, base_data_map
    
    random_key = get_random_string()
    data, base_data = get_block_data_from_table(block, wiki_objects)
    data_map = { random_key: data }
    base_data_map = { random_key: base_data }

    data_map[random_key]['children'] = {}
    base_data_map[random_key]['children'] = {}

    for child in block.get_children():
        course_outline, course_base_outline = get_recursive_blocks_data_from_table(child, wiki_objects, depth - 1)
        data_map[random_key]['children'].update(course_outline)
        base_data_map[random_key]['children'].update(course_base_outline)
    return data_map, base_data_map

def get_course_outline(course_id, N=3):
    """
    Get course outline of a course
    Arguments:
        course_id: Course ID
        N: depth
    Return:
        dict: structured outline of a course based on depth
    """
    wiki_objects = WikiTranslation.objects.filter(target_block__course_id=course_id)
    course_key = CourseKey.from_string(course_id)
    course = get_course_by_id(course_key)
    course_data, base_course_data = get_recursive_blocks_data_from_table(course, wiki_objects, N)
    return course_data, base_course_data

def get_outline_course_to_units(course):
    """
    Get course and base course outline from course-block to depth: unit blocks.
    It will not include components level data (i.e problems, html etc) in returned
    Arguments:
        course: Course Block
    Returns:
        dict: course-outline
        dict: base course-outline
    """
    wiki_objects = WikiTranslation.objects.filter(target_block__course_id=course.course_id)
    return get_recursive_blocks_data_from_table(course, wiki_objects, 3)

def get_outline_unit_to_components(unit):
    """
    Get course and base course outline from units-block to depth: component blocks
    It will include components level data (i.e problems, htmls, transctipt etc) in returned
    Arguments:
        course: Vertical Course Block - Unit
    Returns:
        dict: course-outline
        dict: base course-outline
    """
    wiki_objects = WikiTranslation.objects.filter(target_block__course_id=unit.course_id)
    return get_recursive_blocks_data_from_table(unit, wiki_objects)

def get_course_data_dict(course_key):
    """
    Arguments:
        course_key: Course Key
    Retruns:
        version obj: dic(id, title, language)
    """
    course = get_course_by_id(course_key)
    version_obj = {
        'id': str(course.course_id),
        'title': course.display_name,
        'language': course.language
        }
    return str(course_key), version_obj

def get_courses_of_base_course(base_course_id):
    """
    Retrieve Translated versions of a base course
    {
        course_key_2: {
            "id": "course_key_2",
            "tilte": "Introduction To Computing(Urdu)",
            "language": "ur",
        },
        course_key_3: {
            "id": "course_key_3",
            "tilte": "Introduction To Computing(French)",
            "language": "fr",
        }
    }
    Arguments:
        base_course_id: Course Id of type (str)
    Retruns:
        version obj: Translated versions of base course of type (dict)
    """
    course_varsions = CourseTranslation.objects.filter(base_course_id = base_course_id)
    translated_courses = [get_course_data_dict(course_version.course_id) for course_version in course_varsions]
    return dict(translated_courses)
