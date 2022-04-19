"""
Files containes helping functions assosiated with meta_translations
"""

import json
from logging import getLogger
import os
from common.lib.xmodule.xmodule.video_module.transcripts_utils import Transcript, convert_video_transcript

from xmodule.modulestore.django import modulestore
from xmodule.video_module.transcripts_utils import get_video_transcript_content
from opaque_keys.edx.keys import UsageKey

from openedx.features.wikimedia_features.meta_translations.models import (
    CourseBlock, CourseBlockData, CourseTranslation, WikiTranslation
)
from lms.djangoapps.courseware.courses import get_course_by_id


log = getLogger(__name__)


def get_html_components_data(block):
    """
    Extract data from html type xblock componenets

    Arguments:
        block: html type course-outline block

    Returns:
        dict of extracted data
    """
    return {
        "display_name": block.display_name,
        "content": block.data
    }

def get_json_transcript_data(file_name, content):
    """
    Return dict of subtitiles from content
    """
    if os.path.splitext(file_name) != Transcript.SJSON:
        content = convert_video_transcript(file_name, content, Transcript.SJSON)['content']
    if isinstance(content, str):
        return json.loads(content)
    return json.loads(content.decode("utf-8"))

def get_video_components_data(block):
    """
    Extract data from video type xblock components

    Arguments:
        block: video type course-outline block

    Returns:
        dict of extracted data
    """
    data = get_video_transcript_content(block.edx_video_id, block.transcript_language)
    video_context = { "display_name": block.display_name}
    if data:
        json_content = get_json_transcript_data(data['file_name'], data['content'])
        video_context['transcript'] = json.dumps(json_content['text'])
    return video_context

def get_module_data(block):
    """
    Extract required data from module type blocks i.e sections, subsection and units

    Arguments:
        block: module type course-outline block

    Returns:
        dict of extracted data
    """
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
    """
    Extract required data from course blocks
    Arguments:
        block: course-outline block

    Returns:
        dict of extracted data
    """
    if block.category in COMPONENTS_FUNCTION_MAPPING:
        return {
            'usage_key': str(block.scope_ids.usage_id),
            'category': block.category,
            'data': COMPONENTS_FUNCTION_MAPPING[block.category](block)
        }
    return {}

def get_recursive_blocks_data(block, depth=3, structured=True):
    """
    Retrieve data from blocks.
    if structured True:
        {
            "usage_id": "block_section_usage_id",
            "category": "sequential",
            "data": {
                "display_name": "section 1"
            },
            "children" : [
                {
                    "usage_id": "block_subsection_1_usage_id",
                    "category": "vertical",
                    "data": {
                        "display_name": "subsection 1"
                    },
                },
                {
                    "usage_id": "block_subsection_2_usage_id",
                    "category": "vertical",
                    "data": {
                        "display_name": "subsection 2"
                    },
                },

            ]
        }

    if structured False:
        [
            {
                "usage_id": "block_section_usage_id",
                "category": "sequential",
                "data": {
                    "display_name": "section 1"
            },
            {
                "usage_id": "block_subsection_1_usage_id",
                "category": "vertical",
                "data": {
                    "display_name": "subsection 1"
                },
            },
            {
                "usage_id": "block_subsection_2_usage_id",
                "category": "vertical",
                "data": {
                    "display_name": "subsection 2"
                },
            }
        ]
    Arguments:
        block: block i.e course, section video etc
        depth (int): blocks are tree structured where each block can have multiple children. Depth argument will
          control level of children that we want to traverse.
        structured (bool): if True it will return recursive dict of blocks data else it will return array of all blocks data

    Returns:
        extracted data
    """
    if depth == 0 or not hasattr(block, 'children'):
        block_data = get_block_data(block)
        if structured:
            return block_data
        else:
            return [block_data] if block_data else []

    if structured:
        data = get_block_data(block)
        data['children'] = []
        for child in block.get_children():
            block_data = get_recursive_blocks_data(child, depth - 1, structured)
            if block_data:
                data['children'].append(block_data)
    else:
        block_data = get_block_data(block)
        data = [block_data] if block_data else []
        for child in block.get_children():
            data.extend(get_recursive_blocks_data(child, depth - 1, structured))
    return data


def map_base_course_block(existing_course_blocks, outline_block_dict, course_key):
    """
    Map base-course block -> Sync Course Outline block data to CourseBLock and CourseBLockData table
    - if data does not exist, create new course-block and data entries.
    - if data is updated in course outline, update data in relevant course-block.

    Arguments:
        existing_course_blocks (CourseBlock): existing course-blocks in db for given course-key
        outline_block_dict (dict): contains data of course-outline block
        course_key (CourseKey): course on which mapping needs to perform
    """
    try:
        existing_block = existing_course_blocks.get(block_id=outline_block_dict['usage_key'])
    except CourseBlock.DoesNotExist:
        # Add new blocks in db for new modules/components in course outline.
        log.info("Add base course block.")
        CourseBlock.create_course_block_from_dict(outline_block_dict, course_key)
    else:
        existing_block_data = existing_block.courseblockdata_set.all()

        # Update blocks data in db if any content is edited in course outline.
        for existing_data in existing_block_data:
            outline_block_data = outline_block_dict.get('data', {}).get(existing_data.data_type, "")
            if existing_data.data != outline_block_data:
                log.info("Update course block data of data_type: {} from {} to {}".format(
                    existing_data.data_type, existing_data.data, outline_block_data
                ))
                existing_data.data = outline_block_data
                existing_data.content_updated = True
                existing_data.save()


def map_translated_course_block(existing_course_blocks, outline_block_dict, course_key, base_course_blocks_data):
    """
    Map translated-course block -> Sync Course Outline block to CourseBLock table and create Translation
    mapping entries by comparing data of base-course and translated course block.

    - if block does not exist, create new course-block and translation mapping by comparing
      block-data with base-course data.
    - if data exists, check for existing translation mapping and update block flag to Source if user
      has changed data from front-end.


    Arguments:
        existing_course_blocks (CourseBlock): existing course-blocks in db for given course-key
        outline_block_dict (dict): contains data of course-outline block
        course_key (CourseKey): translated course version on which mapping needs to perform
        base_course_blocks_data: source/base course blocks data so that translation mapping can be created.
    """
    try:
        course_block = existing_course_blocks.get(block_id=outline_block_dict.get("usage_key"))
    except CourseBlock.DoesNotExist:
        # create block mapping in translation table by comparing data of base course blocks and re-run outline data .
        course_block = CourseBlock.create_course_block_from_dict(outline_block_dict, course_key, False)
        for key, value in outline_block_dict.get("data", {}).items():
            WikiTranslation.create_translation_mapping(base_course_blocks_data, key, value, course_block)
    else:
        for key, value in outline_block_dict.get("data", {}).items():
            try:
                wiki_translation = WikiTranslation.objects.get(source_block_data__data_type=key, target_block=course_block)
            except WikiTranslation.DoesNotExist:
                log.info("Re-run block exist but tranlsation mapping is not there fot block: {}".format(
                    json.dumps(outline_block_dict))
                )
                log.info("Trying to find mapping by comparing base course data.")
                WikiTranslation.create_translation_mapping(base_course_blocks_data, key, value, course_block)
            else:
                # if re-run outline data is neither equal to original string (source block data) nor equal to translated string
                # check value of applied, if applied is also True that means user might have updated data from front-end.
                if  value != wiki_translation.translation and value != wiki_translation.source_block_data.data:
                    log.info("Mapping found, but data is not same as original and translated string for block {}".format(
                        json.dumps(outline_block_dict))
                    )
                    log.info("Source data: {}".format(value))
                    log.info("Translated data: {}".format(wiki_translation.translation))
                    if wiki_translation.applied:
                        log.info("Content has been overwritten from front-end -> update flag to source if destination.")
                        course = get_course_by_id(course_block.course_id)
                        course_block.update_flag_to_source(course.language)
                    else:
                        # if applied is False, this means that latest translation is not applied yet.
                        log.info("Latest translation is not applied yet.")


def check_and_map_course_blocks(course_outline_data, course_key, base_course_key=None):
    """
    Traverse course outline blocks and map each block to course-blocks and translation entries in db.

    It will also sync course-outline blocks to db course-blocks by creating, updating and deleting relevant
    course-blocks in db.

    Arguments:
        course_outline_data (Dict): complete course outline blocks data
        course_key (CourseKey): id of the course
        base_course_key (Bool): Contains base-course key if given course_key is translated course version.
    """
    course_outline_blocks_ids = []
    base_course_blocks_data = None
    is_base_course = True
    existing_course_blocks = CourseBlock.objects.filter(course_id=course_key)

    if base_course_key:
        base_course_blocks_data = CourseBlockData.objects.filter(course_block__course_id=base_course_key)
        is_base_course = False

    for block in course_outline_data:
        log.info("-----> Processing block for translation mapping: {}".format(json.dumps(block)))
        course_outline_blocks_ids.append(block.get("usage_key"))

        if is_base_course:
            map_base_course_block(existing_course_blocks, block, course_key)
        else:
            map_translated_course_block(existing_course_blocks, block, course_key, base_course_blocks_data)

    if not is_base_course:
        # delete course-blocks from translated course that exist in db but have been deleted from course-outline.
        existing_course_blocks_ids = [str(block.block_id) for block in existing_course_blocks]
        deleted_block_ids = set(existing_course_blocks_ids) - set(course_outline_blocks_ids)
        log.info("Deleting course blocks that do not exist in course-outline {}.".format(deleted_block_ids))
        for deleted_block_id in deleted_block_ids:
            existing_course_blocks.get(block_id=deleted_block_id).delete()

def get_children_block_ids(block_location):
    """
    Get children_ids from a current block_location
    """
    block = modulestore().get_item(block_location)
    course_blocks = get_recursive_blocks_data(block, 4, structured=False)
    return [UsageKey.from_string(course_block['usage_key']) for course_block in course_blocks]
