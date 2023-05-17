"""
Meta Transaltions related tasks
"""
from django.core import management
from logging import getLogger

from celery import task
from celery_utils.logged_task import LoggedTask

log = getLogger(__name__)

@task(base=LoggedTask)
def send_untranslated_strings_to_meta_from_edx_task(base_course_key):
    """
    Args:
        base_course_key (CourseKey): Base course key
    """
    log.info(f"Initiated task to sync course: {base_course_key} translations to the Meta Server")

    try:
        management.call_command(
            'sync_untranslated_strings_to_meta_from_edx',
            commit=True,
            base_course_key=base_course_key,
        )
        log.info(f'Base Course: {base_course_key} stirngs are updated successfully')
    except Exception as error:
        log.error(f'Error occured in the management command: {str(error)}')
