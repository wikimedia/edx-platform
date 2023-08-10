"""
Utility methods for instructor tasks
"""


from urllib.parse import urljoin
from eventtracking import tracker

from django.urls import reverse

from lms.djangoapps.instructor_task.models import ReportStore

from django.conf import settings


REPORT_REQUESTED_EVENT_NAME = 'edx.instructor.report.requested'

def upload_multiple_course_csv_to_report_store(rows, csv_name, course_id, timestamp, config_name='GRADES_DOWNLOAD'):
    """
    Upload data as a CSV using ReportStore.

    Arguments:
        rows: CSV data in the following format (first column may be a
            header):
            [
                [row1_colum1, row1_colum2, ...],
                ...
            ]
        csv_name: Name of the resulting CSV
        course_id: ID of the course

    Returns:
        report_name: string - Name of the generated report
    """
    report_store = ReportStore.from_config(config_name)
    report_name = "{csv_name}_{timestamp_str}.csv".format(
        csv_name=csv_name,
        timestamp_str=timestamp.strftime("%Y-%m-%d-%H%M")
    )

    report_store.store_rows(course_id, report_name, rows)
    tracker_emit(csv_name)
    return report_name

def tracker_emit(report_name):
    """
    Emits a 'report.requested' event for the given report.
    """
    tracker.emit(REPORT_REQUESTED_EVENT_NAME, {"report_type": report_name, })


def list_report_downloads_links(course_id="all_courses", report_name=None):
    report_store = ReportStore.from_config(config_name='GRADES_DOWNLOAD')

    return [
            dict(name=name, url=url)
            for name, url in report_store.links_for(course_id) if report_name is None or name == report_name
        ]

def get_report_tab_link():
    lms_root_url = settings.LMS_ROOT_URL
    return urljoin(lms_root_url, reverse('admin_dashboard:course_reports'))
