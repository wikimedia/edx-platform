
"""Common settings for Messenger"""


def plugin_settings(settings):
    """
    Common settings for Messenger
    """
    settings.MAKO_TEMPLATE_DIRS_BASE.append(
      settings.OPENEDX_ROOT / 'features' / 'wikimedia_features' / 'meta_translations' / 'templates',
    )

    settings.STATICFILES_DIRS.append (
      settings.OPENEDX_ROOT / 'features' / 'wikimedia_features' / 'meta_translations' / 'static',
    )
