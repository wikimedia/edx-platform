
"""Common settings for Meta Translations"""
from openedx.features.wikimedia_features.meta_translations.transformers.wiki_transformer import ProblemTransformer, VideoTranscriptTransformer

def plugin_settings(settings):
    """
    Common settings for Meta Translations
    """
    settings.MAKO_TEMPLATE_DIRS_BASE.append(
      settings.OPENEDX_ROOT / 'features' / 'wikimedia_features' / 'meta_translations' / 'templates',
    )

    settings.STATICFILES_DIRS.append (
      settings.OPENEDX_ROOT / 'features' / 'wikimedia_features' / 'meta_translations' / 'static',
    )

    # settings for wiki_transformers
    settings.DATA_TYPES_WITH_PARCED_KEYS = ['content', 'transcript']
    settings.TRANSFORMER_CLASS_MAPPING = {
        'problem': ProblemTransformer,
        'video': VideoTranscriptTransformer,
    }
    settings.ACCEPTED_PROBLEM_XML_TAGS = [
      'choiceresponse',
      'optionresponse',
      'multiplechoiceresponse',
      'numericalresponse',
      'stringresponse',
    ]

    settings.WIKI_META_BASE_URL = "https://language-mleb-master.wmcloud.org"
    settings.WIKI_META_CONTENT_MODEL = "translate-messagebundle"
    settings.WIKI_META_MCGROUP_PREFIX = "messagebundle"
    settings.WIKI_META_COURSE_PREFIX = ""
    settings.WIKI_META_API_USERNAME = ""
    settings.WIKI_META_API_PASSWORD = ""
    settings.FETCH_CALL_DAYS_CONFIG_DEFAULT = 3
