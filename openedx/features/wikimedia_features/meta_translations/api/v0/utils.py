"""
Helping functions used in meta translation apis
"""
import json
import string
import random
from logging import getLogger

from opaque_keys.edx.keys import CourseKey
from common.lib.xmodule.xmodule.modulestore.django import modulestore
from lms.djangoapps.courseware.courses import get_course_by_id
from openedx.features.wikimedia_features.meta_translations.meta_client import WikiMetaClient

from openedx.features.wikimedia_features.meta_translations.models import CourseBlock, CourseTranslation, WikiTranslation
from openedx.features.wikimedia_features.meta_translations.wiki_components import COMPONENTS_CLASS_MAPPING

log = getLogger(__name__)

def validate_string(data, is_json = False):
    """
    Function that validates data of type display_name and content
    Returns:
        string: Empty if None else data
    """
    if is_json:
        return json.loads(data) if data else {}
    elif data == None:
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

BLOCK_DATA_TYPES_DATA_VALIDATIONS = {
    'content': validate_string,
    'display_name': validate_string,
    'transcript': validate_string,
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

def validated_and_sort_translated_decodings(base_decodings, translated_decodings):
    """
    Validate and Sort Translated Decodings based on Base Decodings indexs
    Arguments:
        base_decodings: (dict) parsed decondings of base course block
        translated_decodings: (dict) new transaltions from meta server
    Returns:
        is_valid: (bool) check base_decodings and translated_decodings contain same keys and valid translated data
        sorted_translated_decodings: (dict) sorted dict based on base_decodings
    """
    sorted_translated_decodings = {}
    is_valid = True
    for key in base_decodings.keys():
        if translated_decodings.get(key) == None:
            is_valid = False
            sorted_translated_decodings[key] = ''
        else:
            sorted_translated_decodings[key] = translated_decodings[key]
    return is_valid, sorted_translated_decodings

def get_block_data_from_table(block, meta_client, target_langauge):
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
            "status": {
                "applied": false,
                "approved": false,
                "last_fetched": null,
                "approved_by": null
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
        meta_client: MetaClient
        target_langauge: target course language
    Return:
        block_data: dict(usage_key, category, data_block_ids, data)
        translated_block_data: dict(usage_key, category, data)
    """
    if block.category in COMPONENTS_CLASS_MAPPING:
        try:
            usage_key = str(block.scope_ids.usage_id)
            course_block = CourseBlock.objects.get(block_id=usage_key)
            wiki_objects = course_block.wikitranslation_set.all()
            if not wiki_objects:
                log.info("Block Found - Mapping Missing -> Block {} is not added into the outline".format(usage_key))
                return {}, {}
        except CourseBlock.DoesNotExist:
            log.info("Block Not Found - Mapping Missing -> Block {} is not added into the outline".format(usage_key))
        else:
            block_fields = {}
            base_block_fields = {}
            base_usage_key = ''
            course_extra_fields= {}
            parsed_status = { 'parsed_block': False, 'is_fully_translated': True}
            for obj in wiki_objects:
                data_type = obj.source_block_data.data_type
                if WikiTranslation.is_translation_contains_parsed_keys(block.category, data_type):
                    base_decodings = BLOCK_DATA_TYPES_DATA_VALIDATIONS[data_type](obj.source_block_data.parsed_keys)
                    base_decodings = base_decodings if base_decodings else {}
                    translated_decodings = BLOCK_DATA_TYPES_DATA_VALIDATIONS[data_type](obj.translation, is_json = True)
                    is_valid, translated_decodings = validated_and_sort_translated_decodings(base_decodings, translated_decodings)
                    parsed_status['parsed_block'] = True
                    parsed_status['is_fully_translated'] = parsed_status['is_fully_translated'] and is_valid
                    base_block_fields[data_type] = base_decodings
                    block_fields[data_type] = translated_decodings
                else:
                    base_block_fields[data_type] = BLOCK_DATA_TYPES_DATA_VALIDATIONS[data_type](obj.source_block_data.data)
                    block_fields[data_type] = BLOCK_DATA_TYPES_DATA_VALIDATIONS[data_type](obj.translation)
                    parsed_status['is_fully_translated'] = parsed_status['is_fully_translated'] and block_fields[data_type] != ''
                if not base_usage_key:
                    base_usage_key = str(obj.source_block_data.course_block.block_id)
                    course_extra_fields.update(obj.source_block_data.course_block.extra)
            # extra meta server urls
            page_url = None
            page_group_url = None
            if course_extra_fields:
                meta_title = course_extra_fields.get('meta_page_title')
                if meta_title:
                    page_url = meta_client.get_page_redirect_url_for_title(meta_title)
                    page_group_url = meta_client.get_expected_message_group_redirect_url(meta_title, target_langauge)
            
            block_status = course_block.get_block_info()
            version_status = course_block.get_translated_version_status()
            if block_status:
                block_status.update(parsed_status)

            
            course_block_data = {
                'usage_key': usage_key,
                'category': block.category,
                'status': block_status,
                'links': {'page_group_url': page_group_url},
                'version_status': version_status,
                'data': block_fields,
            }
            base_course_block_data = {
                'usage_key': base_usage_key,
                'links': {'page_url': page_url},
                'category': block.category,
                'data': base_block_fields
            }
            return course_block_data, base_course_block_data
    
    return {}, {}

def get_recursive_blocks_data_from_table(block, meta_client, language, depth=4):
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
                "status": {
                    "applied": false,
                    "approved": false,
                    "last_fetched": null,
                    "approved_by": edx
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
                "status": {
                    "applied": false,
                    "approved": false,
                    "last_fetched": null,
                    "approved_by": edx
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
    Return:
        course-outline: structured dict
        base-course-outline: structed dict
    A random key is generated to identify block in course-outline and
    corrensponding block in base-course-outline
    """
    if depth == 0 or not hasattr(block, 'children'):
        random_key = get_random_string()
        data, base_data = get_block_data_from_table(block, meta_client, language)
        data_map, base_data_map = {}, {}
        if data and base_data:
            data_map[random_key] = data
            base_data_map[random_key] = base_data        
        return data_map, base_data_map
    
    random_key = get_random_string()
    data, base_data = get_block_data_from_table(block, meta_client, language)
    if data and base_data:
        data_map = { random_key: data }
        base_data_map = { random_key: base_data }

        data_map[random_key]['children'] = {}
        base_data_map[random_key]['children'] = {}

        for child in block.get_children():
            course_outline, course_base_outline = get_recursive_blocks_data_from_table(child, meta_client, language, depth - 1)
            data_map[random_key]['children'].update(course_outline)
            base_data_map[random_key]['children'].update(course_base_outline)
        return data_map, base_data_map
    return {}, {}

def get_course_outline(course_id, N=3):
    """
    Get course outline of a course
    Arguments:
        course_id: Course ID
        N: depth
    Return:
        dict: structured outline of a course based on depth
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_by_id(course_key)
    meta_client = WikiMetaClient()
    course_data, base_course_data = get_recursive_blocks_data_from_table(course, meta_client, course.language, N)
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
    language = course.language
    meta_client = WikiMetaClient()
    return get_recursive_blocks_data_from_table(course, meta_client, language, 3)

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
    course = get_course_by_id(unit.course_id)
    language = course.language
    meta_client = WikiMetaClient()
    return get_recursive_blocks_data_from_table(unit, meta_client, language)

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

def update_edx_block_from_version(version):
    """
    Update a Edx Block from a version
    Arguments:
        version: TranslationVersion
    """
    data = version.data
    block_location = version.block_id
    block =  modulestore().get_item(block_location)
    updated_block = COMPONENTS_CLASS_MAPPING[block_location.block_type]().update(block, data)
    return updated_block
    