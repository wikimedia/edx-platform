from openedx.core.djangoapps.ace_common.message import BaseMessageType


class PendingMessagesNotification(BaseMessageType):
    """
    A message for notifying users about pending messages on offline messenger app.
    """
    APP_LABEL = 'messenger'

class ThreadMentionNotification(BaseMessageType):
    """
    A message for notifying users that they have been mentioned in a post/response/comment on discussion forum.
    """
    APP_LABEL = 'wikimedia_general'

class ThreadCreationNotification(BaseMessageType):
    """
    A message for notifying instructors when a new  post is created on discussion forum.
    """
    APP_LABEL = 'wikimedia_general'


class ReportReadyNotification(BaseMessageType):
    """
    A message for notifying users that their requested report is ready.
    """
    APP_LABEL = 'admin_dashboard'
