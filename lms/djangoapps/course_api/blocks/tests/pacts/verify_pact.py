"""pact test for user service client"""

import logging
import os

from django.test import LiveServerTestCase
from django.urls import reverse
from pact import Verifier


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PACT_MOCK_HOST = 'localhost'
PACT_MOCK_PORT = 18000
PACT_URL = "http://{}:{}".format(PACT_MOCK_HOST, PACT_MOCK_PORT)

PACT_DIR = os.path.dirname(os.path.realpath(__file__))
PACT_FILE = "sample-block-contract.json"


class MyLiveServerTest(LiveServerTestCase):
    """ Sample Live Server for Pact Verification"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # cls.PACT_URL = PACT_URL
        cls.PACT_URL = cls.live_server_url

        cls.verifier = Verifier(
            provider='lms-course-blocks',
            provider_base_url=cls.PACT_URL,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_verify_pact(self):
        print("\n========LIVE SERVER URL==========")
        print(self.live_server_url)
        print("=================================\n")

        JWT = "NEED-VALID-JWT-TOKEN"

        output, _ = self.verifier.verify_pacts(
            os.path.join(PACT_DIR, PACT_FILE),
            headers=[f'Authorization: JWT {JWT}', ],
            provider_states_setup_url=f"{self.PACT_URL}{reverse('provider-state-view')}",
        )

        assert output == 0
