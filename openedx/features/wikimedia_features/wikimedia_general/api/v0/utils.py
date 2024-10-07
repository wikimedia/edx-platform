"""
Wikimedia Helper functions
"""
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext as _
from common.djangoapps.edxmako.shortcuts import marketing_link


def get_unauthenticated_header_tabs():
    """
    Return header tabs for unauthenticated users
    """
    show_explore_courses = settings.FEATURES.get('COURSES_ARE_BROWSABLE')
    header_tabs = []

    if show_explore_courses:
        header_tabs.append(
            {
                "id": "catalog",
                "name": _('Catalog'),
                "url": marketing_link('COURSES'),
            }
        )

    return header_tabs


def get_authenticated_header_tabs(user):
    """
    Return header tabs for authenticated users
    """
    show_explore_courses = settings.FEATURES.get('COURSES_ARE_BROWSABLE')
    show_messager_app = True

    header_tabs = [
        {
            "id": "courses",
            "name": _('Courses'),
            "url": reverse('dashboard'),
        },
        {
            "id": "programs",
            "name": _('Programs'),
            "url": reverse('program_listing_view'),
        }
    ]
    if show_explore_courses:
        header_tabs.append(
            {
                "id": "catalog",
                "name": _('Catalog'),
                "url": marketing_link('COURSES'),
            }
        )

    if user.is_staff or user.is_superuser:
        header_tabs.append(
            {
                "id": "reports",
                "name": _('Reports'),
                "url": reverse('admin_dashboard:course_reports'),
            }
        )

    if show_messager_app:
        header_tabs.append({
            "id": "inbox",
            "name": _('Inbox'),
            "url": reverse('messenger:messenger_home'),
        })

    # if user.is_superuser:
    #     header_tabs.append(
    #         {
    #             "id": "sysadmin",
    #             "name": _('Sysadmin'),
    #             "url": reverse('sysadmin:sysadmin'),
    #         }
    #     )
    return header_tabs
