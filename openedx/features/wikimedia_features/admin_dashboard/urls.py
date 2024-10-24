"""
Urls for Admin Dashboard
"""
from django.conf.urls import url
from django.conf import settings

from openedx.features.wikimedia_features.admin_dashboard.course_reports import course_reports
from openedx.features.wikimedia_features.admin_dashboard.admin_task.api import (
    average_calculate_grades_csv, progress_report_csv, course_version_report, courses_enrollment_report, all_courses_enrollment_report, user_pref_lang_report, users_enrollment_report, enrollment_activity_report
)

app_name = 'admin_dashboard'
urlpatterns = [
    url(
        r'^average_calculate_grades_csv/{}$'.format(
            settings.COURSE_ID_PATTERN,
        ),
        average_calculate_grades_csv,
        name='average_calculate_grades_csv'
    ),
    url(
        r'^progress_report_csv/{}$'.format(
            settings.COURSE_ID_PATTERN,
        ),
        progress_report_csv,
        name='progress_report_csv'
    ),
    url(
        r'^course_version_report/{}$'.format(
            settings.COURSE_ID_PATTERN,
        ),
        course_version_report,
        name='course_version_report'
    ),
    url(
        r'^courses_enrollment_report',
        courses_enrollment_report,
        name='courses_enrollment_report'
    ),
    url(
        r'^all_courses_enrollment_report',
        all_courses_enrollment_report,
        name='all_courses_enrollment_report'
    ),
    url(
        r'^user_pref_lang_report',
        user_pref_lang_report,
        name='user_pref_lang_report'
    ),
    url(
        r'^users_enrollment_report',
        users_enrollment_report,
        name='users_enrollment_report'
    ),
    url(
        r'^enrollment_activity_report',
        enrollment_activity_report,
        name='enrollment_activity_report'
    ),
    url(r'', course_reports, name='course_reports'),
]
