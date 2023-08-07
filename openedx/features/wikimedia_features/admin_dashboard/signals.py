from django.db.models.signals import post_save
from django.dispatch import receiver

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.features.wikimedia_features.admin_dashboard.models import AdminReportTask
from openedx.features.wikimedia_features.admin_dashboard.tasks import send_report_ready_email_task
from openedx.features.wikimedia_features.admin_dashboard.utils import get_report_tab_link

from celery.states import SUCCESS

from opaque_keys import InvalidKeyError

@receiver(post_save, sender=AdminReportTask)
def send_email_when_report_ready(sender, instance, created, **kwargs):
    if instance.task_state ==  SUCCESS:
        email = instance.requester.email
        report_type = instance.task_type.replace('_', " ").title()
        
        course_ids = instance.course_id.split(',')
        try:
            courses = list(CourseOverview.objects.filter(id__in=course_ids))
        except InvalidKeyError:
            courses = []

        if len(courses) > 1:
            courses_names = list()
            for course in courses:
                courses_names.append(f'"{course.display_name}"')
            courses_names_str = ", ".join(courses_names)
            course_msg = f'the courses {courses_names_str}'
        elif len(courses) == 1:
            course_msg = f'the course "{courses[0].display_name}"'
        else:
            course_msg = f'all courses'


        email_msg = 'The {} report you requested for {} is ready.'.format(report_type, course_msg)
        data = {
            "report_link": get_report_tab_link(),
            "email_msg": email_msg
        }
        send_report_ready_email_task.delay("report_ready", data, "", [email])
