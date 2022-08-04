"""
Views for Messenger
"""
from re import M
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_lazy as _

from common.djangoapps.edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user


@login_required
def render_messenger_home(request):
    meta_data = {
        'button_text': {
            'send': _('Send'),
            'close': _('Close'),
            'cancel': _('Cancel'),
            'reply': _('Reply'),
            'new_message': _('New Message'),
        },
        'placeholder': {
            'type_message': _('Type your message...'),
            'enter_message':  _('Enter Message ...'),
            'username': _('username'),
            'search_users': _('Search Users'),
        },
        'inbox': _('Inbox'),
        'new_message': _('New Message'),
        'users': _('Users'),
        'success': {
            'send_message': _('Message has been sent.'),
            'send_messages': _('Message(s) have been sent.'),
        },
        'error': {
            'send_message': _('Error in sending message. Please try again!'),
            'send_messages': _('Error in sending messages. Please try again!'),
            'read_messages': _('Error in marking messages read.'),
            'load_conversation': _('Unable to load conversations.'),
            'user_conversation': _('Unable to load conversation of user:'),
            'user_search': _('Unable to search users.'),
        }
    }
    return render_to_response('messenger.html', {
        'uses_bootstrap': True,
        'login_user_username': request.user.username,
        'login_user_img': get_profile_image_urls_for_user(request.user, request).get("medium"),
        'meta_data': meta_data,
    })
