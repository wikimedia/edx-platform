from datetime import datetime
from pytz import UTC
from time import time
from common.djangoapps.util.file import course_filename_prefix_generator

from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.instructor_analytics.csvs import format_dictlist
from lms.djangoapps.instructor_task.api_helper import submit_task
from lms.djangoapps.instructor_task.models import ReportStore
from lms.djangoapps.instructor_task.tasks_helper.runner import TaskProgress
from lms.djangoapps.instructor_task.tasks_helper.utils import tracker_emit
from openedx.features.wikimedia_features.admin_dashboard.course_versions.utils import (
    get_last_quarter,
    get_quarter_dates,
    list_all_courses_enrollment_data,
    list_version_report_info_per_course,
    list_version_report_info_total,
    list_quarterly_courses_enrollement_data
)


def upload_course_versions_csv(_xmodule_instance_args, _entry_id, course_id_str, task_input, action_name, user_ids):
    """
    Generate a CSV file containing information of all translated reruns of given base course.

    It will genaretes two types of reports depending upon csv_type
    if csv_type is course_versions -> Generates detailed per-course report containing total enrollments and completion
        information of all translated reruns.
    otherwise for csv_type course_versions_aggregate -> Generates an aggregate report containing total enrollments and completion
        information of all translated reruns.
    """
    start_time = time()
    start_date = datetime.now(UTC)
    num_reports = 1
    task_progress = TaskProgress(action_name, num_reports, start_time)
    current_step = {'step': 'Calculating version'}
    task_progress.update_task_state(extra_meta=current_step)

    # Compute result table and format it
    query_features = task_input.get('features')
    csv_type = task_input.get('csv_type', "course_version")
    course_key = CourseKey.from_string(course_id_str)
    is_per_course_report = True

    if csv_type == 'course_versions':
        query_features_names = [
            'Course ID', 'Course Title', 'Course Language', 'Version Type', '# Enrolled',
            '# Completed', '% Completed', 'Average Grade', 'Skipped Enrollments (grade error)'
        ]
        data, error_data = list_version_report_info_per_course(course_key)

    else:
        query_features_names = [
            'Total Courses', 'Course Ids', 'Course Languages', '# Enrolled',
            '# Completed', '% Completed', 'Average Grade', 'Skipped Enrollments (grade error)'
        ]
        data, error_data = list_version_report_info_total(course_key)
        is_per_course_report = False

    header, rows = format_dictlist(data, query_features)

    error_rows = []
    if error_data:
        error_header, error_rows = format_dictlist(error_data, ['course_id', 'user_id', 'user_name', 'error'])

    task_progress.succeeded = len(rows)
    task_progress.failed = len(error_rows)
    task_progress.attempted = task_progress.succeeded + task_progress.failed
    task_progress.skipped = task_progress.total - task_progress.attempted

    rows.insert(0, query_features_names)

    current_step = {'step': 'Uploading CSV'}
    task_progress.update_task_state(extra_meta=current_step)

    # Perform the upload
    upload_course_versions_csv_to_report_store(rows, error_rows, course_key, start_date, is_per_course_report)

    return task_progress.update_task_state(extra_meta=current_step)


def upload_course_versions_csv_to_report_store(rows, error_rows, course_key, timestamp, is_per_course_report, config_name='GRADES_DOWNLOAD'):
    """
    Upload credits data as a CSV using ReportStore. It will not append given base course name in generated filename.
    It will also generates Error report along with versions report if any grade error will occur.
    Arguments:
        rows: CSV data in the following format (first column may be a
            header):
            [
                [row1_colum1, row1_colum2, ...],
                ...
            ]
        error_rows: list pf dict contsing information about grade errors
            i.e [{'course_id_1', 'user_id_1', 'dummy', 'reason of error'}]
        course_key: Base course id
        timestramp: current timestramp
        is_per_course_report: Boolean value indicating if report is detailed one or aggregate one
    """
    report_store = ReportStore.from_config(config_name)

    csv_name = "versions_info_detailed" if is_per_course_report else "versions_info_total"
    report_name = u'{course_prefix}_{csv_name}_{timestamp_str}.csv'.format(
        course_prefix=course_filename_prefix_generator(course_key),
        csv_name=csv_name,
        timestamp_str=timestamp.strftime('%Y-%m-%d-%H%M')
    )
    report_store.store_rows(str(course_key), report_name, rows)

    if error_rows:
        report_name = "ERRORS_" + report_name
        error_rows.insert(0, ['Course ID', 'User ID', 'Username', 'Error'])
        report_store.store_rows(str(course_key), report_name, error_rows)
    tracker_emit(csv_name)


def upload_all_courses_enrollement_csv(_xmodule_instance_args, _entry_id, course_id_str, task_input, action_name, user_ids):
    """
    Generate a CSV file containing information of all courses enrollments.
    """
    start_time = time()
    start_date = datetime.now(UTC)
    num_reports = 1
    task_progress = TaskProgress(action_name, num_reports, start_time)
    current_step = {'step': 'Calculating All Courses Enrollment Stats'}
    task_progress.update_task_state(extra_meta=current_step)

    # Compute result table and format it
    query_features = task_input.get('features')
    csv_type = task_input.get('csv_type', "all_enrollement_stats")

    query_features_names = [
        'Course URL', 'Course title', 'Course available since', 'Parent course URL', 'Parent course title', 'Total learners enrolled', 'Total learners completed', 'Percentage of learners who completed the course',
    ]
    data = list_all_courses_enrollment_data()

    header, rows = format_dictlist(data, query_features)

    task_progress.attempted = task_progress.succeeded = len(rows)
    task_progress.skipped = task_progress.total - task_progress.attempted

    rows.insert(0, query_features_names)

    current_step = {'step': 'Uploading CSV'}
    task_progress.update_task_state(extra_meta=current_step)

    # Perform the upload
    report_store = ReportStore.from_config('GRADES_DOWNLOAD')

    csv_name = "all_courses_enrollements"
    report_name = '{csv_name}_{timestamp_str}.csv'.format(
        csv_name=csv_name,
        timestamp_str=start_date.strftime('%Y-%m-%d-%H%M')
    )
    report_store.store_rows(course_id_str, report_name, rows)

    return task_progress.update_task_state(extra_meta=current_step)


def upload_quarterly_courses_enrollement_csv(_xmodule_instance_args, _entry_id, course_id_str, task_input, action_name, user_ids):
    """
    Generate a CSV file containing information of quarterly courses enrollments.
    """
    start_time = time()
    start_date = datetime.now(UTC)
    num_reports = 1
    task_progress = TaskProgress(action_name, num_reports, start_time)
    current_step = {'step': 'Calculating version'}
    task_progress.update_task_state(extra_meta=current_step)

    # Compute result table and format it
    query_features = task_input.get('features')
    csv_type = task_input.get('csv_type', "course_version")
    options = task_input.get('options', {})

    query_features_names = [
        'Course ID', 'Base Course ID', 'Course Title', 'Course Language', 'Username', 'Date Enrolled',
        'Date Completed', 'Cohort Enrollee', 'Student Blocked'
    ]
    if options['year'] and options['quarter']:
        quarter = get_quarter_dates(options['year'], options["quarter"])
    else:
        quarter = get_last_quarter()

    data = list_quarterly_courses_enrollement_data(quarter)

    header, rows = format_dictlist(data, query_features)

    task_progress.attempted = task_progress.succeeded = len(rows)
    task_progress.skipped = task_progress.total - task_progress.attempted

    rows.insert(0, query_features_names)

    current_step = {'step': 'Uploading CSV'}
    task_progress.update_task_state(extra_meta=current_step)

    # Perform the upload
    report_store = ReportStore.from_config('GRADES_DOWNLOAD')
    csv_name = f"courses_enrollements({quarter[0]}-{quarter[1]})"
    report_name = '{csv_name}_{timestamp_str}.csv'.format(
        csv_name=csv_name,
        timestamp_str=start_date.strftime('%Y-%m-%d-%H%M')
    )
    report_store.store_rows(course_id_str, report_name, rows)

    return task_progress.update_task_state(extra_meta=current_step)
