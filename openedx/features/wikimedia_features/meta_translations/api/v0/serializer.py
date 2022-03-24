"""
Serializers for Messenger v0 API(s)
"""
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.translation import ugettext as _
from rest_framework import serializers
from openedx.features.wikimedia_features.messenger.models import Inbox, Message
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user


class OutlineSerializer(serializers.Serializer):
    course_key = serializers.CharField()
    base_course_key = serializers.CharField()

class SubsectionSerializer(serializers.Serializer):
    subsection_key = serializers.CharField()
    base_subsection_key = serializers.CharField()