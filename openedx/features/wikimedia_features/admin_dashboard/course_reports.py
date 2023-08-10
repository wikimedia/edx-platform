"""
Views for Course Reports
"""
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseForbidden
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse

from common.djangoapps.edxmako.shortcuts import render_to_response
from common.djangoapps.util.cache import cache_if_anonymous
from lms.djangoapps.courseware.access import has_access
from lms.djangoapps.courseware.courses import get_course_by_id, get_courses


def require_user_permission():
    """
    Decorator with argument that requires a specific permission of the requesting
    user. If the requirement is not satisfied, returns an
    HttpResponseForbidden (403).

    Assumes that request is in args[0].
    """
    def decorator(func):
        def wrapped(*args):
            request = args[0]
            if request.user.is_staff or request.user.is_superuser:
                return func(*args)
            else:
                return HttpResponseForbidden()
        return wrapped
    return decorator

import json
from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation
@login_required
@require_user_permission()
@ensure_csrf_cookie
@cache_if_anonymous()
def course_reports(request):
    courses_list = []
    sections = {"key": {}}

    courses_list = get_courses(request.user)
    course = get_course_by_id(courses_list[0].id, depth=0)

    access = {
        'admin': request.user.is_staff,
        'instructor': bool(has_access(request.user, 'instructor', courses_list[0])),
    }
    sections["key"] = section_data_download(course, access)

    current_year = datetime.today().year
    year_options = sorted(range(2021, current_year+1), reverse=True)

    return render_to_response(
        "course_report/course-reports.html",
        {
            'base_courses_list': json.dumps([str(course_id) for course_id in CourseTranslation.get_base_courses_list()]),
            'courses': courses_list,
            'section_data': sections,
            "year_options": year_options,
        }
    )

def section_data_download(course, access):
    """ Provide data for the corresponding dashboard section """
    course_key = course.id
    section_data = {
        'access': access,
        'get_students_features_url': reverse('get_students_features', kwargs={'course_id': str(course_key)}),
        'list_report_downloads_url': reverse('list_report_downloads', kwargs={'course_id': str(course_key)}),
        'calculate_grades_csv_url': reverse('calculate_grades_csv', kwargs={'course_id': str(course_key)}),
        'problem_grade_report_url': reverse('problem_grade_report', kwargs={'course_id': str(course_key)}),
        'get_anon_ids_url': reverse('get_anon_ids', kwargs={'course_id': str(course_key)}),
        'get_students_who_may_enroll_url': reverse(
            'get_students_who_may_enroll', kwargs={'course_id': str(course_key)}
        ),
        'average_calculate_grades_csv_url': reverse('admin_dashboard:average_calculate_grades_csv', kwargs={'course_id': str(course_key)}),
        'progress_report_csv_url': reverse('admin_dashboard:progress_report_csv', kwargs={'course_id': str(course_key)}),
        'course_version_report_url': reverse('admin_dashboard:course_version_report', kwargs={'course_id': str(course_key)}),
        'courses_enrollments_csv_url': reverse('admin_dashboard:courses_enrollment_report'),
        'all_courses_enrollments_csv_url': reverse('admin_dashboard:all_courses_enrollment_report'),
    }
    if not access.get('data_researcher'):
        section_data['is_hidden'] = True
    return section_data
