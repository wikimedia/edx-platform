import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.certificates.data import CertificateStatuses
from lms.djangoapps.certificates.models import GeneratedCertificate
from lms.djangoapps.badges.events.course_complete import course_badge_check

LOGGER = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Django management command to award badges to students who have received
    certificates for a given course_id.

    Usage:
        python manage.py award_badges <course_id>
    """

    help = 'Award badges to students who have received certificates for a given course_id'

    def add_arguments(self, parser):
        parser.add_argument('course_id', type=str, help='The ID of the course')

    def handle(self, *args, **kwargs):
        course_id = kwargs['course_id']
        try:
            self.award_badges_for_course(course_id)
        except Exception as e:
            LOGGER.error("An error occurred while awarding badges: %s", str(e), exc_info=True)

    def award_badges_for_course(self, course_id):
        LOGGER.info("Fetching certificates for course_id: %s", course_id)
        generated_certificates = GeneratedCertificate.eligible_certificates.filter(
            course_id=course_id,
            status=CertificateStatuses.downloadable
        ).values('user')

        if not generated_certificates:
            LOGGER.info("No certificates found for course_id: %s", course_id)
            return

        for certificate in generated_certificates:
            user_id = certificate['user']
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    course_key = CourseKey.from_string(course_id)
                    course_badge_check(user, course_key)
                    LOGGER.info("Awarded badge to user %s for the  course %s", user.username, course_id)
                except User.DoesNotExist:
                    LOGGER.error("User with id %s does not exist", user_id)
                except Exception as e:
                    LOGGER.error("An error occurred while processing user %s: %s", user_id, str(e), exc_info=True)
