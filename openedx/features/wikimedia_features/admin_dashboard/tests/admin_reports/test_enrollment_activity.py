from unittest.mock import MagicMock, PropertyMock, patch
from datetime import datetime

from django.utils import timezone
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.features.wikimedia_features.admin_dashboard.admin_task.api import SUCCESS_MESSAGE_TEMPLATE
from openedx.features.wikimedia_features.admin_dashboard.course_versions.utils import list_enrollment_activity
from openedx.features.wikimedia_features.admin_dashboard.tasks import (
    task_enrollment_activity_report,
    upload_enrollment_activity_csv,
)


User = get_user_model()


class EnrollmentActivityReportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("admin_dashboard:enrollment_activity_report")

        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")

    @patch("openedx.features.wikimedia_features.admin_dashboard.admin_task.api.submit_task")
    def test_enrollment_activity_report_success(self, mock_submit_task):
        response = self.client.post(self.url)

        # Verify that submit_task is called with expected arguments
        mock_submit_task.assert_called_once_with(
            response.wsgi_request,
            _("enrollment_acctivity_report"),
            task_enrollment_activity_report,
            "all_courses",
            {
                "features": ["username", "course_title", "enrollment_date", "completion_date"],
                "csv_type": _("enrollment_acctivity_report"),
            },
            "",
        )

        # Check that the response is JSON and contains the correct success message
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())
        self.assertEqual(
            response.json()["status"], SUCCESS_MESSAGE_TEMPLATE.format(report_type="User Enrollments Expanded Report")
        )


class EnrollmentActivityReportTaskTest(TestCase):

    @patch("openedx.features.wikimedia_features.admin_dashboard.tasks.partial")
    @patch("openedx.features.wikimedia_features.admin_dashboard.tasks.upload_enrollment_activity_csv")
    @patch("openedx.features.wikimedia_features.admin_dashboard.tasks.run_main_task")
    def test_task_enrollment_activity_report(self, mock_run_main_task, mock_upload_csv, mock_partial):
        entry_id = 1
        xmodule_instance_args = {"task_id": 1}
        user_id = 1

        # Mock the funtion to simulate task running
        mock_run_main_task.return_value = "task_completed"
        mock_partial.return_value = mock_upload_csv

        result = task_enrollment_activity_report(entry_id, xmodule_instance_args, user_id)

        # Ensure `run_main_task` and `partial` were called with expected arguments
        mock_partial.assert_called_once_with(mock_upload_csv, xmodule_instance_args)
        mock_run_main_task.assert_called_once_with(entry_id, mock_upload_csv, "generated", user_id)
        self.assertEqual(result, "task_completed")


class TestUploadEnrollmentActivityCSV(TestCase):

    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.task_helper.datetime")
    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.task_helper.list_enrollment_activity")
    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.task_helper.format_dictlist")
    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.task_helper.ReportStore")
    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.task_helper.TaskProgress")
    def test_upload_enrollment_activity_csv(
        self, mock_task_progress, mock_report_store, mock_format_dictlist, mock_list_enrollment_activity, mock_datetime
    ):
        # Set up mock datetime and enrollment activity data
        mock_datetime.now.return_value = datetime(2024, 11, 6, 12, 0, 0)  # Controlled datetime
        mock_list_enrollment_activity.return_value = [("user1", "course1", "2024-01-01", "2024-02-01")]
        mock_format_dictlist.return_value = ([], [["user1", "course1", "2024-01-01", "2024-02-01"]])

        # Mock ReportStore
        mock_report_store_instance = MagicMock()
        mock_report_store.from_config.return_value = mock_report_store_instance

        # Mock TaskProgress to return a mock object
        mock_task_progress_instance = MagicMock()
        mock_task_progress.return_value = mock_task_progress_instance

        # Define task input
        task_input = {
            "features": ["User", "Course Title", "Enrollment Date", "Completion Date"],
            "csv_type": "enrollment_activity",
        }
        action_name = "upload_enrollment"
        user_ids = ["user1"]
        course_id_str = "course1"
        _xmodule_instance_args = None
        _entry_id = None

        # Call the function under test
        upload_enrollment_activity_csv(
            _xmodule_instance_args, _entry_id, course_id_str, task_input, action_name, user_ids
        )

        mock_list_enrollment_activity.assert_called_once()
        mock_report_store_instance.store_rows.assert_called_once_with(
            course_id_str,
            "enrollment_activity_2024-11-06-1200.csv",
            [
                ["User", "Course Title", "Enrollment Date", "Completion Date"],
                ["user1", "course1", "2024-01-01", "2024-02-01"],
            ],
        )


class TestListEnrollmentActivity(TestCase):

    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.utils.get_users_with_enrollments")
    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.utils.get_course_completion_date")
    def test_list_enrollment_activity_valid_data(
        self, mock_get_course_completion_date, mock_get_users_with_enrollments
    ):
        """
        Test that the function returns the correct enrollment activity with valid data.
        """
        # Set up mock data
        mock_enrollment1 = MagicMock(course=MagicMock(display_name="Course 1"), is_active=1, created=timezone.now())
        mock_enrollment2 = MagicMock(course=MagicMock(display_name="Course 2"), is_active=1, created=timezone.now())

        mock_user1 = MagicMock(username="user1")
        mock_user1.courseenrollment_set.all.return_value = [mock_enrollment1, mock_enrollment2]

        mock_get_users_with_enrollments.return_value = [mock_user1]

        # Mock course completion dates
        mock_get_course_completion_date.return_value = timezone.now()

        activity_data = list_enrollment_activity()

        # Validate the data structure
        self.assertEqual(len(activity_data), 2)
        self.assertEqual(activity_data[0]["username"], "user1")
        self.assertEqual(activity_data[0]["course_title"], "Course 1")
        self.assertIn("enrollment_date", activity_data[0])
        self.assertIn("completion_date", activity_data[0])

    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.utils.get_users_with_enrollments")
    def test_list_enrollment_activity_empty_enrollments(self, mock_get_users_with_enrollments):
        """
        Test that the function returns an empty list if there are no enrollments.
        """
        mock_get_users_with_enrollments.return_value = []

        # Call the function
        activity_data = list_enrollment_activity()

        # Assert that the returned list is empty
        self.assertEqual(activity_data, [])

    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.utils.get_users_with_enrollments")
    @patch("openedx.features.wikimedia_features.admin_dashboard.course_versions.utils.get_course_completion_date")
    def test_list_enrollment_activity_course_does_not_exist(
        self, mock_get_course_completion_date, mock_get_users_with_enrollments
    ):
        """
        Test that the function handles cases where the course does not exist.
        """
        # Set up mock data where one enrollment has no course
        mock_enrollment = MagicMock(created=timezone.now())
        type(mock_enrollment).course = PropertyMock(side_effect=CourseOverview.DoesNotExist)
        mock_user = MagicMock(username="user1")
        mock_user.courseenrollment_set.all.return_value = [mock_enrollment]

        mock_get_users_with_enrollments.return_value = [mock_user]

        mock_get_course_completion_date.return_value = None

        activity_data = list_enrollment_activity()

        # Assert results when course is missing
        print(activity_data)
        self.assertEqual(len(activity_data), 0)
