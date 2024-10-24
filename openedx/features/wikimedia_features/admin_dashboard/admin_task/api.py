import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.db import transaction
from django.http.response import HttpResponseBadRequest, HttpResponseForbidden
from django.contrib.auth.models import User  # lint-amnesty, pylint: disable=imported-auth-user
from django.core.exceptions import MultipleObjectsReturned
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.instructor import permissions
from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.instructor.views.api import require_course_permission as course_permission
from common.djangoapps.util.json_request import JsonResponse
from openedx.features.wikimedia_features.admin_dashboard.admin_task.api_helper import AlreadyRunningError, QueueConnectionError, submit_task
from openedx.features.wikimedia_features.admin_dashboard.tasks import (
    task_average_calculate_grades_csv,
    task_progress_report_csv,
    task_course_version_report,
    task_courses_enrollment_report,
    task_all_courses_enrollment_report,
    task_user_pref_lang_report,
    task_users_enrollment_info_report,
    task_enrollment_activity_report
)
from openedx.features.wikimedia_features.admin_dashboard.course_versions import task_helper

log = logging.getLogger(__name__)
TASK_LOG = logging.getLogger('edx.celery.task')

SUCCESS_MESSAGE_TEMPLATE = _("The {report_type} report is being created. "
                             "To view the status of the report, see Pending Tasks below.")


def require_course_permission(permission):
    """
    Decorator with argument that requires a specific permission of the requesting
    user. If the requirement is not satisfied, returns an
    HttpResponseForbidden (403).

    Assumes that request is in args[0].
    Assumes that course_id is in kwargs['course_id'].
    """
    def decorator(func):
        def wrapped(*args, **kwargs):
            request = args[0]
            courses = kwargs['course_id'].split(",")
            for course in courses:
                course_id  = get_course_by_id(CourseKey.from_string(course))
                if request.user.has_perm(permission, course_id):
                    course_permission = True
                else:
                    return HttpResponseForbidden()
            if course_permission:
                return func(*args, **kwargs)
        return wrapped
    return decorator

def common_exceptions_400(func):
    """
    Catches common exceptions and renders matching 400 errors.
    (decorator without arguments)
    """

    def wrapped(request, *args, **kwargs):
        use_json = (request.is_ajax() or
                    request.META.get("HTTP_ACCEPT", "").startswith("application/json"))
        try:
            return func(request, *args, **kwargs)
        except User.DoesNotExist:
            message = _('User does not exist.')
        except MultipleObjectsReturned:
            message = _('Found a conflict with given identifier. Please try an alternative identifier')
        except (AlreadyRunningError, QueueConnectionError, AttributeError) as err:
            message = str(err)

        if use_json:
            return HttpResponseBadRequest(message)
        else:
            return HttpResponseBadRequest(message)

    return wrapped

@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_course_permission(permissions.CAN_RESEARCH)
@common_exceptions_400
def average_calculate_grades_csv(request, course_id):
    """
    AlreadyRunningError is raised if the course's grades are already being updated.
    """
    report_type = _('grade')
    submit_average_calculate_grades_csv(request, course_id)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@course_permission(permissions.CAN_RESEARCH)
@common_exceptions_400
def progress_report_csv(request, course_id):
    """
    Request a CSV showing students' progress for all units in the
    course.

    AlreadyRunningError is raised if the course's grades are already being
    updated.
    """
    report_type = _('progress')
    submit_progress_report_csv(request, course_id)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_course_permission(permissions.CAN_RESEARCH)
@common_exceptions_400
def course_version_report(request, course_id):
    """
    Handles request to generate CSV of base course versions info for all translated reruns.
    """
    report_type = request.POST.get('csv_type', 'course_versions')
    if report_type == 'course_versions':
        query_features = [
            'course_id', 'course_title', 'course_language', 'version_type', 'total_active_enrolled',
            'total_completion', 'completion_percent', 'average_grade', 'error_count'
        ]
        success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type="Versions Detailed Report")

    else:
        query_features = [
            'total_courses', 'course_ids', 'course_languages', 'total_active_enrolled',
            'total_completion', 'completion_percent', 'average_grade', 'error_count'
        ]
        success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type="Versions Aggregate Report")

    submit_course_version_report(request, course_id, query_features, report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def all_courses_enrollment_report(request):
    """
    Handles request to generate CSV of stats of all courses enrollments
    """
    report_type = _("all_enrollments_stats")

    success_status = SUCCESS_MESSAGE_TEMPLATE.format(
        report_type="All Courses enrollment Report"
    )
    query_features = [
        "course_url",
        "course_title",
        "available_since",
        "parent_course_url",
        "parent_course_title",
        "total_learners_enrolled",
        "total_learners_completed",
        "completed_percentage",
        "total_cert_generated",
    ]
    submit_courses_enrollment_report(
        request, query_features, report_type, task_all_courses_enrollment_report
    )

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def courses_enrollment_report(request):
    """
    Handles request to generate CSV of stats of all courses enrollments.
    """
    report_type = _("enrollment")

    success_status = SUCCESS_MESSAGE_TEMPLATE.format(
        report_type="Courses enrollment Report"
    )
    query_features = [
        "course_id",
        "base_course_id",
        "course_title",
        "course_language",
        "student_username",
        "date_enrolled",
        "date_completed",
        "cohort_enrollee",
        "student_blocked",
    ]
    options = request.POST
    submit_courses_enrollment_report(
        request, query_features, report_type, task_courses_enrollment_report, options
    )

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def user_pref_lang_report(request):
    """
    Handles request to generate CSV of users preferred language.
    """
    report_type = _("user_pref_lang")
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(
        report_type="Users Preferred Language Report"
    )
    task_input = {
        'features': ["username", "dark_lang", "pref_lang"],
        'csv_type': report_type,
    }

    submit_task(request, report_type, task_user_pref_lang_report, 'all_courses', task_input, "")
    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def users_enrollment_report(request):
    """
    Handles request to generate CSV of all users enrollments info.
    """
    report_type = _("all_users_enrollment")
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(
        report_type="Users Enrollments Report"
    )
    task_input = {
        'features': ["username", "enrollments_count", "completions_count"],
        'csv_type': report_type,
    }

    submit_task(request, report_type, task_users_enrollment_info_report, 'all_courses', task_input, "")
    return JsonResponse({"status": success_status})

@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def enrollment_activity_report(request):
    """
    Handles request to generate CSV of all users enrollments detailed info. This report has a separate row
    for each enrollment.
    """
    report_type = _("enrollment_acctivity_report")
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(
        report_type="User Enrollments Expanded Report"
    )
    task_input = {
        'features': ["username", "course_title", "enrollment_date", "completion_date"],
        'csv_type': report_type,
    }

    submit_task(request, report_type, task_enrollment_activity_report, 'all_courses', task_input, "")
    return JsonResponse({"status": success_status})


def submit_average_calculate_grades_csv(request, course_key):
    """
    AlreadyRunningError is raised if the course's grades are already being updated.
    """
    task_type = 'grade_course'
    task_class = task_average_calculate_grades_csv
    task_input = {}
    task_key = ""

    return submit_task(request, task_type, task_class, course_key, task_input, task_key)


def submit_progress_report_csv(request, course_id):
    """
    Submits a task to generate a CSV grade report containing problem
    values.
    """
    task_type = 'progress_info_csv'
    task_class = task_progress_report_csv
    task_input = {}
    task_key = ""
    return submit_task(request, task_type, task_class, course_id, task_input, task_key)


def submit_course_version_report(request, course_key,  features, task_type):
    """
    Submits a task to generate a CSV of translated versions report
    """
    task_class = task_course_version_report
    task_input = {
        'features': features,
        'csv_type': task_type
    }
    task_key = ""

    return submit_task(request, task_type, task_class, course_key, task_input, task_key)


def submit_courses_enrollment_report(
    request, features, task_type, task_class, options=None
):
    """
    Submits a task to generate a CSV of all courses enrollments report
    """
    task_input = {
        'features': features,
        'csv_type': task_type,
        'options': options
    }
    task_key = ""

    return submit_task(request, task_type, task_class, 'all_courses', task_input, task_key)
