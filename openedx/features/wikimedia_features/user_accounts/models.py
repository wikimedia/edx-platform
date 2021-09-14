import collections
import logging

from django.contrib.auth.models import User
from django.db import models
from jsonfield.fields import JSONField

logger = logging.getLogger(__name__)
APP_LABEL = 'user_accounts'


class WikimediaUserProfile(models.Model):
    user = models.OneToOneField(User, unique=True, db_index=True,
                                related_name='wikimedia_profile', on_delete=models.CASCADE)
    extensions = JSONField(
        null=False,
        blank=True,
        default=dict,
        load_kwargs={'object_pairs_hook': collections.OrderedDict}
    )

    class Meta:
        app_label = APP_LABEL
        verbose_name_plural = 'Wikimedia user profiles'

    def get_extension_value(self, name, default=None):
        try:
            return self.extensions.get(name, default)
        except AttributeError as error:
            logger.exception(u'Invalid JSON data. \n [%s]', error)

    def set_extension_value(self, name, value=None):
        try:
            self.extensions[name] = value
            self.save()
        except AttributeError as error:
            logger.exception(u'Invalid JSON data. \n [%s]', error)
