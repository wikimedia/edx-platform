from django.test import RequestFactory
from django.contrib.auth import get_user_model

from common.djangoapps.student.models import CourseEnrollment
from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.grades.api import CourseGradeFactory

from openedx.features.wikimedia_features.meta_translations.models import CourseTranslation
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from edx_proctoring.api import get_last_exam_completion_date

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


def list_courses_enrollement_data():
    """
    Get course reports
    """
    courses_data = []
    courses = CourseOverview.objects.all()
    for course in courses:
        enrollments = CourseEnrollment.objects.filter(course_id=course.id, is_active=True).order_by('created')
        for enrollment in enrollments:
            try:
                course_traslation = CourseTranslation.objects.get(course_id=course.id)
                base_course_id = str(course_traslation.base_course_id)
            except CourseTranslation.DoesNotExist:
                base_course_id = ''
            else:
                user = User.objects.get(id=enrollment.user_id)
                username = user.get_username()
                completion_date = get_last_exam_completion_date(course.id, username)
                courses_data.append({
                    'course_id': str(course.id),
                    'base_course_id': str(base_course_id),
                    'course_title': course.display_name,
                    'course_language': course.language,
                    'student_username': username,
                    'date_enrolled': enrollment.created.strftime("%Y-%m-%d"),
                    'date_completed': completion_date.strftime("%Y-%m-%d") if completion_date else '',
                    'cohort_enrollee': 'N' if course.self_paced else 'Y',
                    'student_blocked': 'N' if user.is_active else 'Y',
                })
    return courses_data
