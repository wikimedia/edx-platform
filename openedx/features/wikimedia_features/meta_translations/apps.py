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
                    PluginURLs.REGEX: '^meta_translations/',
                    PluginURLs.RELATIVE_PATH: 'urls',
                },
        },
        PluginSettings.CONFIG: {
            ProjectType.CMS: {
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: 'settings.common'},
            }
        }
    }



    