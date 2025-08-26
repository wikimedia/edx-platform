import logging
from django.utils.functional import cached_property
from django.conf import settings
from social_core.exceptions import AuthException
from common.djangoapps.third_party_auth.identityserver3 import IdentityServer3

log = logging.getLogger(__name__)


class WikimediaIdentityServer(IdentityServer3):
    """
    An extension of the IdentityServer3 for use with Wikimedia's IdP service.
    """
    name = "wikimediaIdentityServer"
    DEFAULT_SCOPE = ["mwoauth-authonlyprivate"]
    ID_KEY = "sub"

    def _parse_name(self, name):
        fullname = name
        if ' ' in fullname:
            firstname, lastname = fullname.split(' ', 1)
        else:
            firstname = name
            lastname = ""
        # Truncate the firstname to max 30 characters. User model doesn't accepts firstname above 30 characters.
        firstname = firstname if len(firstname)<=30 else firstname[:30]
        return fullname, firstname, lastname

    def auth_headers(self):
        headers = super().auth_headers()
        client = getattr(settings, "PLATFORM_NAME", "wikilearn")
        site = getattr(settings, "LMS_ROOT_URL", "https://learn.wiki/")
        contact_mail = getattr(settings, "CONTACT_EMAIL", "comdevteam@wikimedia.org")
        headers['User-Agent'] = f'{client}/0.13 ({site}; {contact_mail})'
        
        return headers
    
    def user_data(self, access_token, *args, **kwargs):
        """
        Consumes the access_token to get data about the user logged
        into the service. Also, sets the headers for the authentication
        APIs.
        """
        url = self.get_config().get_setting('user_info_url')
        header = self.auth_headers()
        # The access token returned from the service's token route.
        header["Authorization"] = "Bearer %s" % access_token
        return self.get_json(url, headers=header)

    def get_user_details(self, response):
        """
        Returns detail about the user account from the service
        """

        try:
            name = response.get("realname", "") or response["username"]
            fullname, firstname, lastname = self._parse_name(name)

            details = {
                "fullname": fullname,
                "email": response["email"],
                "first_name": firstname,
                "last_name": lastname,
                "username": response["username"]
            }
            return details
        except KeyError:
            log.exception("User profile data is unappropriate or not given")
            raise AuthException("Wikimedia", "User profile data is unappropriate or not given")

    @cached_property
    def _id3_config(self):
        from common.djangoapps.third_party_auth.models import OAuth2ProviderConfig
        return OAuth2ProviderConfig.current(self.name)
