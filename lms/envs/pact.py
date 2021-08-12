"""
Settings for Pact Verification Tests.
"""

from .test import *  # pylint: disable=wildcard-import, unused-wildcard-import

#### Allow Pact Provider States URL ####
PROVIDER_STATES_URL = True

######################### Add Authentication MIddleware for Pact Verification Calls #########################
MIDDLEWARE = MIDDLEWARE + ['lms.djangoapps.course_api.blocks.tests.pacts.middleware.AuthenticationMiddleware', ]
