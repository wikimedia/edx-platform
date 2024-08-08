import requests

from logging import getLogger

from django.contrib.auth import get_user_model
from django.db.models import F, Value, Case, When, CharField
from django.db.models.query import QuerySet
from django.db.models.functions import Concat
from django.core.management.base import BaseCommand

log = getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    """
    Django management command to sync user usernames with Wikimedia usernames.

    This command matches the usernames in the local database with the Wikimedia
    usernames, and updates the local usernames if they differ from the ones provided
    by Wikimedia.
    """

    help = "Matches the usernames with Wikimedia and updates the changed ones in Wikilearn"

    def add_arguments(self, parser):
        """
        Adds command-line arguments to the management command.

        Arguments:
            parser (ArgumentParser): The argument parser to which arguments should be added.
                - usernames (list): List of specific usernames to sync. If not provided,
                  all usernames will be checked and synced.
        """
        parser.add_argument(
            "usernames",
            nargs="*",
            type=str,
            help="Provide list of usernames. If not provided, all usernames will be synced with wikimedia usernames.",
        )

    def handle(self, *args, **options):
        """
        Main entry point for the command.

        Retrieves the users whose usernames need to be checked and updated.
        Filters the users if specific usernames are provided. Logs the process and
        prints the statistics of the operation.

        Arguments:
            args: Additional positional arguments.
            options: Command-line options, including the list of usernames.
        """
        usernames = options["usernames"]
        users = self._get_tpa_users()

        if usernames:
            users = users.filter(username__in=usernames)

        total = users.count()

        log.info("Syncing %s users with Wikimedia usernames", total)

        stats = self._update_user_with_wikimedia_username(users)
        self._print_stats(total, stats)

    def _get_tpa_users(self) -> QuerySet[User]:
        """
        Retrieves users who registered with the third-party authentication (TPA) provider.

        These are users whose usernames need to be potentially updated based on
        Wikimedia usernames. Excludes users whose first name is missing or whose
        username already matches their wiki_username.

        Returns:
            QuerySet[User]: A queryset of users to be processed.
        """
        users = (
            User.objects.select_related("profile")
            .annotate(
                wiki_username=Case(
                    When(last_name="", then=F("first_name")),
                    When(last_name__isnull=True, then=F("first_name")),
                    default=Concat(F("first_name"), Value(" "), F("last_name"), output_field=CharField()),
                    output_field=CharField(),
                )
            )
            .exclude(first_name__isnull=True)
            .exclude(first_name="")
            .exclude(
                username=F("wiki_username")
            )  # Because no point in updating username with wiki_username later if it is already same.
        )

        return users

    def _update_user_with_wikimedia_username(self, users: QuerySet[User]) -> dict:
        """
        Updates the usernames of users based on their Wikimedia username.

        This method checks if the current username matches the Wikimedia username.
        If the usernames differ, the local username is updated. It logs each operation
        and returns statistics of the update process.

        Arguments:
            users (QuerySet[User]): A queryset of users to be processed.

        Returns:
            dict: A dictionary containing statistics about the update process.
                  - correct_username: Number of usernames that were already correct.
                  - updated_username: Number of usernames that were updated.
                  - skipped_username: Number of usernames that were skipped.
        """
        total = len(users)
        stats = {
            "correct_username": 0,
            "updated_username": 0,
            "skipped_username": 0,
            "updated_users": [],
        }
        for i, user in enumerate(users):
            index = i + 1
            if self._username_exists(user.username):
                # This check is to avoid updating username if it is already correct according to Wikimedia.
                log.info(f"{index}/{total}: SKIPPED: {user.username} is CORRECT")
                stats["correct_username"] += 1
            elif self._username_exists(user.wiki_username):
                log.info(f"{index}/{total}: UPDATING: {user.username} with {user.wiki_username}")
                user_values = {
                    "username": user.username,
                    "wiki_username": user.wiki_username,
                    "profile_name": user.profile.name,
                    "email": user.email,
                }

                self._update_user(user)

                stats["updated_username"] += 1
                stats["updated_users"].append(user_values)
            else:
                # This means both the username and the computed wiki_username are incorrect.
                log.info(f"{index}/{total}: SKIPPED: {user.username}")
                stats["skipped_username"] += 1

        return stats

    def _username_exists(self, username: str) -> bool:
        """
        Checks if a username exists in Wikimedia's global account database.

        Arguments:
            username (str): The username to be checked.

        Returns:
            bool: True if the username exists in Wikimedia, False otherwise.
        """
        USERNAME_VERIFY_URL = f"https://en.wikipedia.org/wiki/Special:CentralAuth?target={username}"
        ERROR_MSG = "There is no global account for"

        response = requests.get(USERNAME_VERIFY_URL)

        return ERROR_MSG not in response.text

    def _update_user(self, user: User):
        """
        Updates the username of a user in the local database.

        Arguments:
            user (User): The user object whose username is to be updated.
        """
        user.username = user.wiki_username
        user.save()

    def _print_stats(self, total: int, stats: dict):
        """
        Prints statistics about the update process.

        Arguments:
            total (int): The total number of users processed.
            stats (dict): A dictionary containing statistics about the update process.
        """
        log.info(f"Total mismatched users: {total}")
        log.info(f"Correct usernames: {stats['correct_username']}")
        log.info(f"Updated usernames: {stats['updated_username']}")
        log.info(f"Skipped usernames: {stats['skipped_username']}")
        log.info(f"Updated users: {stats['updated_users']}")
