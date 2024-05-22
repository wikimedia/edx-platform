from datetime import datetime, timedelta
import pytz 
from logging import getLogger

from django.core.management.base import BaseCommand
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
import openedx.core.djangoapps.django_comment_common.comment_client as cc
from openedx.features.wikimedia_features.wikimedia_general.tasks import send_weekly_digest_new_post_notification_to_instructors

log = getLogger(__name__)

class Command(BaseCommand):
    """
    This management command logs all course IDs in the system and threads that were created at least one week ago.
    It is used to fetch and send notifications for threads that are newly created within the last week across all courses.

    The command logs details about each course and retrieves threads based on specified criteria, handling pagination if necessary. If threads are found that match the criteria, it sends a notification to instructors using a designated task.

    Attributes:
        help (str): Description of what the command does.
    """
    help = 'Logs all course IDs in the system and threads created at least one week ago'

    def handle(self, *args, **options):
        """
        Executes the management command which involves fetching courses, retrieving threads, and sending notifications.

        This method iterates through all courses retrieved from the CourseOverview model, logs their IDs, and fetches threads that were created in the last week. If threads are found, it sends notifications to instructors.

        Args:
            *args: Variable length argument list.
            **options: Arbitrary keyword arguments.

        Side Effects:
            Logs course IDs and notification statuses to the console.
            Calls external methods to send notifications if relevant threads are found.
        """
        one_week_ago = datetime.now(pytz.utc) - timedelta(days=7)  # Adjusted to one week ago
        all_courses = CourseOverview.get_all_courses()
        log.info('Fetching all course IDs and their respective threads...')

        for course in all_courses:
            log.info(f'Course ID: {course.id}')
            query_params = {
                'course_id': str(course.id),
                'page': 1,
                'per_page': 20  # Adjust based on expected volume
            }

            threads = self.get_threads(query_params, one_week_ago)
            
            if threads:  # Check if the list of threads is not empty
                send_weekly_digest_new_post_notification_to_instructors(threads)
            else:
                log.info(f"No recent threads to notify for course ID: {course.id}")

    def get_threads(self, query_params, one_week_ago):
        """
        Retrieves threads that were created between one week ago and the current time from the discussion service.

        This method queries the discussion service for threads based on provided parameters, filtering them to include only those created within the specified time frame. It handles pagination automatically and fetches all relevant threads.

        Args:
            query_params (dict): Parameters used for querying the discussion service including 'course_id', 'page', and 'per_page'.
            one_week_ago (datetime): The datetime object representing one week ago from the current time, used as a filter for thread creation dates.

        Returns:
            list: A list of threads that were created within the last week and match the other query parameters.

        Raises:
            Exception: If there is an issue fetching the full thread data from the discussion service.
        """
        # Fetching threads using a search function which returns minimal thread data
        paginated_results = cc.Thread.search(query_params)
        threads = paginated_results.collection

        # Filter and convert to full objects
        recent_threads = []
        current_time = datetime.now(pytz.utc)  # Get the current UTC time

        for thread in threads:
            created_at = datetime.strptime(thread['created_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
            # Ensure that the thread was created within the last week
            if one_week_ago <= created_at <= current_time:
                full_thread = cc.Thread.find(thread['id'])
                recent_threads.append(full_thread)

        return recent_threads
