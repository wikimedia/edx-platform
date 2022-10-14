
"""Production settings for Meta Translations"""

def plugin_settings(settings):
    """
    Production settings for Meta Translations
    """
    settings.WIKI_META_BASE_URL = settings.ENV_TOKENS.get('WIKI_META_BASE_URL', settings.WIKI_META_BASE_URL)
    settings.WIKI_META_BASE_API_URL = settings.ENV_TOKENS.get('WIKI_META_BASE_API_URL', settings.WIKI_META_BASE_API_URL)
    settings.WIKI_META_CONTENT_MODEL = settings.ENV_TOKENS.get('WIKI_META_CONTENT_MODEL', settings.WIKI_META_CONTENT_MODEL)
    settings.WIKI_META_MCGROUP_PREFIX = settings.ENV_TOKENS.get('WIKI_META_MCGROUP_PREFIX', settings.WIKI_META_MCGROUP_PREFIX)
    settings.WIKI_META_COURSE_PREFIX = settings.ENV_TOKENS.get('WIKI_META_COURSE_PREFIX', settings.WIKI_META_COURSE_PREFIX)
    settings.WIKI_META_API_USERNAME = settings.ENV_TOKENS.get('WIKI_META_API_USERNAME', settings.WIKI_META_API_USERNAME)
    settings.WIKI_META_API_PASSWORD = settings.ENV_TOKENS.get('WIKI_META_API_PASSWORD', settings.WIKI_META_API_PASSWORD)
    settings.FETCH_CALL_DAYS_CONFIG_DEFAULT = settings.ENV_TOKENS.get('FETCH_CALL_DAYS_CONFIG_DEFAULT', settings.FETCH_CALL_DAYS_CONFIG_DEFAULT)
