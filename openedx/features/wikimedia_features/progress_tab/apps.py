"""
Progress Tab App Config
"""
from django.apps import AppConfig
from edx_django_utils.plugins import PluginURLs, PluginSettings
from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType


class ProgressTabConfig(AppConfig):
    name = 'openedx.features.wikimedia_features.progress_tab'

    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                    PluginURLs.NAMESPACE: 'progress_tab',
                    PluginURLs.REGEX: '^progress_tab/',
                    PluginURLs.RELATIVE_PATH: 'urls',
                },
        },
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: 'settings.common'},
            },
        }
    }
