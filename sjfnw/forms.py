import logging
import re

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError

logger = logging.getLogger('sjfnw')

class CustomPasswordResetForm(PasswordResetForm):

  def get_users(self, email):
    """ Parent method searches by email - we want to search by username """
    users = User.objects.filter(username__iexact=email)
    valid_users = [u for u in users if u.has_usable_password()]
    if len(valid_users) == 0:
      logger.warn('Password reset form found no users for email %s', email)
    return valid_users


class PhoneNumberField(forms.Field):
  """ Accepts 10-digit phone numbers regardless of input format
      Standardizes to xxx-xxx-xxxx format """

  default_error_messages = {
    'invalid': u'Enter a 10-digit phone number.',
  }

  def __init__(self, *args, **kwargs):
    super(PhoneNumberField, self).__init__(*args, **kwargs)

  def clean(self, value):
    """ Strip extraneous characters before proceeding with validation """

    if isinstance(value, (str, unicode)):
      value = re.sub(ur'[()\-\s\u2010]', '', value) # u2010 is hyphen
      if value and len(value) != 10:
        raise ValidationError(self.error_messages['invalid'])

    return super(PhoneNumberField, self).clean(value)

  def to_python(self, value):
    """ Validate that input can be converted to integer
        Return phone number as a formatted string, or '' if empty """

    value = super(PhoneNumberField, self).to_python(value)
    if value in validators.EMPTY_VALUES:
      return ''

    try:
      int(str(value))
    except (ValueError, TypeError):
      raise ValidationError(self.error_messages['invalid'])

    return value[:3] + u'-' + value[3:6] + u'-' + value[6:]


class IntegerCommaField(forms.Field):
  """ Accepts numbers formatted with commas. Stores them as integers.

     (Mostly copied from IntegerField, with some modifications) """

  default_error_messages = {
    'invalid': u'Enter a whole number. (Format: 11009 or 11,009)',
    'max_value': u'Must be less than or equal to %(limit_value)s.',
    'min_value': u'Must be greater than or equal to %(limit_value)s.',
  }

  def __init__(self, max_value=None, min_value=None, *args, **kwargs):
    self.max_value, self.min_value = max_value, min_value
    super(IntegerCommaField, self).__init__(*args, **kwargs)

    if max_value is not None:
      self.validators.append(validators.MaxValueValidator(max_value))
    if min_value is not None:
      self.validators.append(validators.MinValueValidator(min_value))

  def clean(self, value):
    """ Remove commas and cents before proceeding with validation """

    if isinstance(value, (str, unicode)):
      value = value.replace(',', '')
      amount = re.match(r'(\d+)(\.\d{2})?$', value)
      if amount:
        value = amount.group(1)

    return super(IntegerCommaField, self).clean(value)

  def to_python(self, value):
    """ Coerce to integer or return None for empty values """

    value = super(IntegerCommaField, self).to_python(value)
    if value in validators.EMPTY_VALUES:
      return None

    try:
      value = int(str(value))
    except (ValueError, TypeError):
      raise ValidationError(self.error_messages['invalid'])

    return value
