
"""Common Settings"""


def plugin_settings(settings):
    """
    Required Common settings
    """
    settings.FEATURES['ENABLE_DEFAULT_COURSE_MODE_CREATION'] = False
    ADVANCED_PROBLEM_TYPES = [
        {
            'component': 'drag-and-drop-v2',
            'boilerplate_name': None
        },
        {
            'component': 'staffgradedxblock',
            'boilerplate_name': None
        },
        {
            'component': 'poll',
            'boilerplate_name': None
        },
        {
            'component': 'done',
            'boilerplate_name': None
        },
        {
            'component': 'lti_consumer',
            'boilerplate_name': None
        }
    ]
