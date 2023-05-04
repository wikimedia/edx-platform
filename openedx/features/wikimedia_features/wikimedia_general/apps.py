"""
Wikimedia General App Config
"""
from django.apps import AppConfig
from edx_django_utils.plugins import PluginURLs, PluginSettings
from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType


class WikimediaGeneralConfig(AppConfig):
    name = 'openedx.features.wikimedia_features.wikimedia_general'

    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.CMS: {
                    PluginURLs.NAMESPACE: 'wikimedia_general',
                    PluginURLs.REGEX: '^wikimedia_general/',
                    PluginURLs.RELATIVE_PATH: 'urls',
                },
            ProjectType.LMS: {
                    PluginURLs.NAMESPACE: 'wikimedia_general',
                    PluginURLs.REGEX: '^wikimedia_general/',
                    PluginURLs.RELATIVE_PATH: 'urls',
                },
        },
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: 'settings.common'},
            },
            ProjectType.CMS: {
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: 'settings.common'},
            }
        }
    }

    def ready(self):
        from . import signals  # pylint: disable=unused-import
