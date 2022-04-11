"""
Meta Translations App Config
"""
from django.apps import AppConfig
from edx_django_utils.plugins import PluginURLs, PluginSettings
from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType


class MetaTranslationsConfig(AppConfig):
    name = 'openedx.features.wikimedia_features.meta_translations'
    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.CMS: {
                PluginURLs.NAMESPACE: 'meta_translations',
                PluginURLs.REGEX: '^meta/',
                PluginURLs.RELATIVE_PATH: 'urls',
            }
        }
    }

    def ready(self):
        from . import signals  # pylint: disable=unused-import
