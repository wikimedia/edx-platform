import requests

from logging import getLogger

from django.contrib.auth import get_user_model
from django.db.models import F, Value, Case, When, CharField
from django.db.models.functions import Concat
from django.core.management.base import BaseCommand

log = getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    """ """

    help = "Matches the usernames with Wikimedia and updates the changed ones in Wikilearn"

    def add_arguments(self, parser):
        parser.add_argument(
            "usernames",
            nargs="*",
            type=str,
            help="Provide list of usernames. If not provided, all usernames will be synced with wikimedia usernames.",
        )

    def handle(self, *args, **options):
        """
        Get all TPA users whose usernames were cleaned and filter by usernames if provided.
        Get their usernames from the third party provider in this case wikimedia
        and update their username in Wikilearn.
        """
        usernames = options["usernames"]
        users = self._get_tpa_users()

        if usernames:
            users = users.filter(username__in=usernames)

        self._update_user_with_wikimedia_username(users)

    def _get_tpa_users(self):
        """
        Gets all the platform users who registered with the third party provider.

        It is assumed that users without first name were registered before TPA was required.
        Also excludes where username is the combination first and last name already.
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
            )  # because no point in updating username with wiki_username later if it is already same.
        )

        return users

    def _update_user_with_wikimedia_username(self, users: list[User]):
        """
        Checks if "wiki_username" was the original username provided by Wikimedia
        and updates the Wikilearn username with it.
        """
        total = len(users)
        for i, user in enumerate(users):
            index = i + 1
            if self._username_exists(user.wiki_username):
                self._update_user(user)
                log.info(f"{index}/{total}: UPDATED {user.username} with {user.wiki_username}")
            else:
                log.info(f'{index}/{total}: SKIPPED {user["username"]}')

    def _username_exists(self, username: str) -> bool:
        """
        Checks if username exists in the Wikimedia's global account.
        """
        USERNAME_VERIFY_URL = f"https://en.wikipedia.org/wiki/Special:CentralAuth?target={username}"
        ERROR_MSG = "There is no global account for"

        response = requests.get(USERNAME_VERIFY_URL)

        return ERROR_MSG not in response.text

    def _update_user(self, user: User):
        user.username = user.wiki_username
        user.save()
