from django.apps import AppConfig

from edx_django_utils.plugins import PluginURLs, PluginSettings
from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType


class UserAccountsConfig(AppConfig):
    name = 'openedx.features.wikimedia_features.user_accounts'

    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: 'user_accounts',
                PluginURLs.REGEX: None,
                PluginURLs.RELATIVE_PATH: None,
            }
        }
    }

    def ready(self):
        from . import signals  # pylint: disable=unused-import
