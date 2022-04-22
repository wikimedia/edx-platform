"""
Client to handle WikiMetaClient requests.
"""
import json
import logging
import requests
from django.conf import settings
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

logger = logging.getLogger(__name__)


class WikiMetaClient(object):
    """
    Client for Meta API requests.
    """
    def __init__(self):
        """
        Constructs a new instance of the Wiki Meta client.
        """
        self._BASE_API_END_POINT = configuration_helpers.get_value(
                'WIKI_META_BASE_API_URL', settings.WIKI_META_BASE_API_URL)
        self._CONTENT_MODEL = configuration_helpers.get_value(
                'WIKI_META_CONTENT_MODEL', settings.WIKI_META_CONTENT_MODEL)
        self._MCGROUP_PREFIX = configuration_helpers.get_value(
                'WIKI_META_MCGROUP_PREFIX', settings.WIKI_META_MCGROUP_PREFIX)

        logger.info(
            "Create meta client with api_url: {}, content_model: {}".format(
                self._BASE_API_END_POINT, self._CONTENT_MODEL
            )
        )

        if not self._BASE_API_END_POINT or not self._CONTENT_MODEL or not self._MCGROUP_PREFIX :
            raise Exception("Missing WIKI Meta Configurations.")


    async def parse_response(self, response):
        """
        Parses and return the response.
        """
        try:
            data = await response.json()
        except ValueError:
            logger.error("Unable to extract json data from Meta response.")
            logger.error(response.text)
            data = None

        if data is not None and response.status in [200, 201]:
            if data.get('error'):
                logger.error("Meta API returned error code in response: %s.", json.dumps(data))
                return False, data

            logger.info("Meta API returned success response: %s.", json.dumps(data))
            return True, data

        else:
            logger.error("Meta API return response with status code: %s.", response.status_code)
            logger.error("Meta API return Error response: %s.", json.dumps(data))
            return False, data


    async def handle_request(self, request_call, params=None, data=None):
        """
        Handles all Meta API calls.
        """
        logger.info("Sending Meta request.")
        response = await request_call(url=self._BASE_API_END_POINT, params=params, data=data)
        return await self.parse_response(response)


    async def fetch_login_token(self, session):
        logger.info("Initiate Meta login token request.")
        params = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
            "formatversion": 2
        }
        success, response_data = await self.handle_request(session.get, params=params, data=None)
        if success:
            token = response_data.get('query', {}).get('tokens', {}).get('logintoken', {})
            logger.info("User token has been fetched: %s.", token)
            return token


    async def login_request(self, session):
        token  = await self.fetch_login_token(session)
        if not token:
            raise Exception("Meta Client Error: Unable to get Login Token from Meta.")

        logger.info("Initiate Meta login request with generated login-token.")
        post_data = {
           "action": "login",
           "lgname": "Testabcxyz123@lastlastbot",
           "lgpassword": "qtvu1dnlk8t635jla8e0b10rees3n07j",
           "lgtoken": token,
           "format": "json",
           "formatversion": 2
        }

        success, data = await self.handle_request(session.post, params=None, data=post_data)
        if success:
            logger.info("Login request is successfull")
        else:
            raise Exception("Meta Client Error: Failed login request.")


    async def fetch_csrf_token(self, session):
        logger.info("Initiate Meta CSRF token request.")
        params = {
            "action": "query",
            "meta": "tokens",
            "format": "json",
            "formatversion": 2
        }

        success, response_data = await self.handle_request(session.get, params=params, data=None)
        if success:
            csrf_token = response_data.get('query', {}).get('tokens', {}).get('csrftoken', {})
            logger.info("CSRF token has been set: %s.", csrf_token)
            return csrf_token


    async def create_update_message_group(self, title, text, session, csrf_token, summary="update_content"):
        data = {
            "action": "edit",
            "format": "json",
            "title": title,
            "text": text,
            "summary": summary,
            "contentmodel": self._CONTENT_MODEL,
            "token": csrf_token,
        }

        success, response_data = await self.handle_request(session.post, params=None, data=data)
        if success:
            response_edit_dict = response_data.get("edit", {})
            logger.info("Message group has been updated for component: %s and pageid: %s .",
                        response_edit_dict.get('title'),
                        response_edit_dict.get('pageid')
            )
            return response_edit_dict


    async def sync_translations(self, mcgroup, mclanguage, session):
        logger.info("{}-{}".format(self._MCGROUP_PREFIX, mcgroup))
        params = {
            "action": "query",
            "format": "json",
            "list": "messagecollection",
            "utf8": 1,
            "formatversion": 2,
            "mcgroup": "{}-{}".format(self._MCGROUP_PREFIX, mcgroup),
            "mclanguage": mclanguage,
            "mcprop": "translation|properties",
        }
        success, response_data = await self.handle_request(session.get, params=params, data=None)
        if success:
            print(response_data)
