from datetime import date
import calendar

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.conf import settings

from common.djangoapps.student.models import CourseEnrollment
from lms.djangoapps.branding import get_visible_courses
from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.grades.api import CourseGradeFactory

from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from edx_proctoring.api import get_last_exam_completion_date
from openedx.features.wikimedia_features.wikimedia_general.utils import get_course_enrollment_and_completion_stats

User = get_user_model()


def list_version_report_info_per_course(course_key):
    """
    Returns lists of versions detailed data and error data for a given base course
    versions_data: list of dict - required to generated detailed report of translated reruns for given base course.
        list will contain all translated reruns info along with base course info.
    error_data: list of dict - If grading error occurs during processing, those students data will be skiped from
        average grade calculation and error rows will be added in error list.
    [
        ...
        {
            'course_id': 'translted_rerun_course_id_1',
            'course_title': 'Translated rerun version in French',
            'course_language': 'Fr',
            'version_type': 'translated rerun',
            'total_active_enrolled': 10,
            'total_completion': 5,
            'completion_percent': 0.5,
            'average_grade': 0.5,
            'error_count': 0
        }
        ...
    ]
    """
    versions_data = []
    error_data = []

    def update_report_data(course_key, course_type):
        from openedx.features.course_experience.utils import get_course_outline_block_tree
        nonlocal error_data, versions_data
        sum_grade_percent = 0
        error_count = 0
        enrollments = CourseEnrollment.objects.filter(course_id=course_key, is_active=True).order_by('created')
        users = [enrollment.user for enrollment in enrollments]
        total_enrollments = len(users)
        total_students_with_no_errors = 0
        completion_count = 0
        request = RequestFactory().get(u'/')
        course = get_course_by_id(course_key)
        for student, course_grade, error in CourseGradeFactory().iter(users=users, course_key=course_key):
            course_blocks = get_course_outline_block_tree(
                request, str(course_key), student
            )
            if course_blocks.get('complete'):
                completion_count += 1

            if error is not None:
                error_data.append({
                    'course_id': str(course_key),
                    'user_id': student.id,
                    'user_name': student.username,
                    'error': str(error)
                })
                error_count += 1
            else:
                total_students_with_no_errors += 1
                sum_grade_percent += course_grade.percent

        average_grade = total_students_with_no_errors and (sum_grade_percent / total_students_with_no_errors)
        versions_data.append({
            'course_id': str(course_key),
            'course_title': course.display_name,
            'course_language': course.language,
            'version_type': course_type,
            'total_active_enrolled': total_enrollments,
            'total_completion': completion_count,
            'completion_percent': total_enrollments and completion_count / total_enrollments,
            'average_grade': average_grade,
            'error_count': error_count
        })

    course_translation = CourseTranslation.objects.filter(base_course_id=course_key)
    if course_translation.exists():
        update_report_data(course_key, 'base course')
        for version_obj in course_translation:
            update_report_data(version_obj.course_id, 'translated rerun')

    return versions_data, error_data


def list_version_report_info_total(course_key):
    """
    Returns lists of versions aggregate data and error data for a given base course
    versions_data: list of dict - required to generated aggregated report of translated reruns for given base course.
        list will contain aggregate info for all translated reruns  along with base course.
    error_data: list of dict - If grading error occurs during processing, those students data will be skiped from
        average grade calculation and error rows will be added in error list.
    [
        ...
        {
            'course_ids': '[tarnslated_rerun_id_1, translated_rerun_id_2]',
            'course_languages': ['en', 'fr'],
            'total_active_enrolled': 20,
            'total_completion': 10,
            'completion_percent': 0.5,
            'average_grade': 0.5,
            'error_count': 0
        }
        ...
    ]
    """
    error_data = []
    course_ids = []
    course_languages = []

    report = {
        'total_courses': 0,
        'sum_grade_percent': 0,
        'error_count': 0,
        'total_completion': 0,
        'total_active_enrolled': 0,
        'total_students_with_no_errors': 0,
    }

    def update_report_data_with_details(course_key):
        from openedx.features.course_experience.utils import get_course_outline_block_tree
        request = RequestFactory().get(u'/')

        nonlocal error_data, course_ids, course_languages, report
        report['total_courses'] += 1
        course_ids.append(str(course_key))

        course = get_course_by_id(course_key)
        course_languages.append(str(course.language))

        enrollments = CourseEnrollment.objects.filter(course_id=course_key, is_active=True).order_by('created')
        users = [enrollment.user for enrollment in enrollments]
        report['total_active_enrolled'] += len(users)

        for student, course_grade, error in CourseGradeFactory().iter(users=users, course_key=course_key):
            course_blocks = get_course_outline_block_tree(
                request, str(course_key), student
            )
            if course_blocks.get('complete'):
                report['total_completion'] += 1

            if error is not None:
                error_data.append({
                    'course_id': str(course_key),
                    'user_id': student.id,
                    'user_name': student.username,
                    'error': str(error)
                })
                report['error_count'] += 1
            else:
                report['total_students_with_no_errors'] += 1
                report['sum_grade_percent'] += course_grade.percent

    course_translation = CourseTranslation.objects.filter(base_course_id=course_key)
    if course_translation.exists():
        update_report_data_with_details(course_key)
        for version_obj in course_translation:
            update_report_data_with_details(version_obj.course_id)

    total_enrollments = report.get('total_active_enrolled')
    completion_count = report.get('total_completion')
    total_students_with_no_errors = report.get('total_students_with_no_errors')
    sum_grade_percent = report.get('sum_grade_percent')
    report.update({
        'course_ids': course_ids,
        'course_languages': course_languages,
        'completion_percent': total_enrollments and completion_count / total_enrollments,
        'average_grade': total_students_with_no_errors and (sum_grade_percent / total_students_with_no_errors),
    })
    return [report], error_data


def get_quarter_dates(year, quarter):
    """Returns the start and end date of the given quarter
    """
    year, quarter = int(year), int(quarter)

    date_format = "%Y-%m-%d"

    start_month = (quarter * 3) - 2
    start = date(year, start_month, 1)

    last_month = start_month + 2
    last_day = calendar.monthrange(year, last_month)[-1]
    end = date(year, last_month, last_day)

    return [start.strftime(date_format), end.strftime(date_format)]


def get_last_quarter():
    """Returns the start and end date of the last yearly quarter
    """
    ref = date.today()
    date_format = "%Y-%m-%d"
    if ref.month < 4:
        return [date(ref.year - 1, 10, 1).strftime(date_format), date(ref.year - 1, 12, 31).strftime(date_format)]
    elif ref.month < 7:
        return [date(ref.year, 1, 1).strftime(date_format), date(ref.year, 3, 31).strftime(date_format)]
    elif ref.month < 10:
        return [date(ref.year, 4, 1).strftime(date_format), date(ref.year, 6, 30).strftime(date_format)]
    return [date(ref.year, 7, 1).strftime(date_format), date(ref.year, 9, 30).strftime(date_format)]


def get_cms_course_url(course_key):
    """
    Get course url for studio
    """
    return f"https://{settings.CMS_BASE}/course/{course_key}"


def list_all_courses_enrollment_data():
    """
    Get all courses enrollment report
    """

    courses = get_visible_courses()
    courses_data = []


    for course in courses:
        
        parent_course_url = ''
        parent_course_title = ''
        try:
            course_traslation = CourseTranslation.objects.get(course_id=course.id)
            parent_course_url = get_cms_course_url(str(course_traslation.base_course_id))
            parent_course_title = get_course_by_id(course_traslation.base_course_id).display_name
        except CourseTranslation.DoesNotExist:
            pass
        
        total_learners_completed, total_learners_enrolled, completed_percentage = \
            get_course_enrollment_and_completion_stats(course.id)
        courses_data.append({
            'course_url' : get_cms_course_url(str(course.id)),
            'course_title': course.display_name,
            'available_since': course.enrollment_start.strftime("%Y-%m-%d") if course.enrollment_start else '',
            "parent_course_url": parent_course_url,
            "parent_course_title": parent_course_title,
            "total_learners_enrolled": total_learners_enrolled,
            "total_learners_completed": total_learners_completed,
            "completed_percentage": completed_percentage,
        })
    
    return courses_data



def list_quarterly_courses_enrollement_data(quarter):
    """
    Get course reports
    """
    courses_data = []
    courses = CourseOverview.objects.all()
    for course in courses:
        enrollments = CourseEnrollment.objects.filter(
            created__range=quarter,
            course_id=course.id,
            is_active=True,
        ).order_by('created')

        language = get_course_by_id(course.id).language
        base_course_id = ''
        try:
            course_traslation = CourseTranslation.objects.get(course_id=course.id)
            base_course_id = str(course_traslation.base_course_id)
        except CourseTranslation.DoesNotExist:
            pass

        for enrollment in enrollments:
            user = User.objects.get(id=enrollment.user_id)
            username = user.get_username()
            completion_date = get_last_exam_completion_date(course.id, username)
            courses_data.append({
                'course_id': str(course.id),
                'base_course_id': str(base_course_id),
                'course_title': course.display_name,
                'course_language': language,
                'student_username': username,
                'date_enrolled': enrollment.created.strftime("%Y-%m-%d"),
                'date_completed': completion_date.strftime("%Y-%m-%d") if completion_date else '',
                'cohort_enrollee': 'N' if course.self_paced else 'Y',
                'student_blocked': 'N' if user.is_active else 'Y',
            })
    return courses_data
