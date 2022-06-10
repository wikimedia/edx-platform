"""
Files contains generic helping functions associated with meta_translations
"""

import json
from logging import getLogger

from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import UsageKey

from openedx.features.wikimedia_features.meta_translations.models import (
    CourseBlock, CourseTranslation, TranslationVersion, WikiTranslation
)
from openedx.features.wikimedia_features.meta_translations.mapping_utils import get_recursive_blocks_data
from lms.djangoapps.courseware.courses import get_course_by_id

log = getLogger(__name__)


def get_children_block_ids(block_location):
    """
    Get children_ids from a current block_location
    """
    block = modulestore().get_item(block_location)
    course_blocks = get_recursive_blocks_data(block, 4, structured=False)
    return [UsageKey.from_string(course_block['usage_key']) for course_block in course_blocks]

def is_destination_block(block_id):
    """
    Get direction status
    """
    try:
        course_block = CourseBlock.objects.get(block_id=block_id)
        return course_block.is_destination()
    except CourseBlock.DoesNotExist:
        return False

def is_destination_course(course_id):
    """
    Check if the course is destination course i.e course is translated rerun
    """
    return CourseTranslation.objects.filter(course_id=course_id).exists()

def get_block_status(block_id):
    """
    Get data of course block
    {
        'mapped': True,
        'applied': True,
        'approved': True,
        'approved_by': username,
        'last_fetched': data,
    }
    """
    block_status = {}
    block_status['mapped'] = False
    try:
        course_block = CourseBlock.objects.get(block_id=block_id)
        block_info = course_block.get_block_info()
        if block_info:
            block_status = block_info
            block_status['mapped'] = True
    except CourseBlock.DoesNotExist:
        log.info('No CourseBlock found for block {}'.format(block_id))
    return block_status

def update_course_to_source(course_key):
    """
    Update course level flag from Destination to Source.
    It will also update all underlying blocks flag to source. Updating block-level flag to source means
    that it will not be tracked any more for translations. Any updated translations won't be fetched from wiki meta server.
    """
    try:
        translation_link = CourseTranslation.objects.get(course_id=course_key)
        log.info('Start converting course with id: {} to Source'.format(str(course_key)))
        # update all underlying component's flag to source
        course = get_course_by_id(course_key)
        log.info('Check and update all underlying blocks to Source'.format(str(course_key)))
        for course_block in CourseBlock.objects.filter(course_id=course_key):
            course_block.update_flag_to_source(course.language)
            log.info('Update course block with id: {} to Source'.format(str(course_key)))
        translation_link.delete()
        log.info('Course Flag with id: {} has been successfully updated to Source'.format(str(course_key)))
    except CourseTranslation.DoesNotExist:
        log.info('Course with id: {} is already a Source Course'.format(str(course_key)))

def reset_fetched_translation_and_version_history(base_course_block_data):
    """
    Reset translation and all versions from history
    """
    if base_course_block_data:
        for wiki_tarnslation in WikiTranslation.objects.filter(source_block_data=base_course_block_data).select_related("target_block"):
            wiki_tarnslation.translation = None
            wiki_tarnslation.approved = False
            wiki_tarnslation.save()

            target_block = wiki_tarnslation.target_block
            target_block.applied_version = None
            target_block.applied_translation = False
            target_block.save()

            TranslationVersion.objects.filter(block_id=target_block.block_id).delete()
