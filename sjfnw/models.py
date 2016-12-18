from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator

# hacky patch to give User username max length of 100 (instead of default 30)

# pylint: disable=protected-access,unsubscriptable-object
def patch_user_model(model):
  field = model._meta.get_field("username")
  field.max_length = 100
  field.help_text = field.help_text.replace('30', '100')

  # manually update field's validator
  for validator in field.validators:
    if isinstance(validator, MaxLengthValidator):
      validator.limit_value = 100

  # patch admin site forms
  from django.contrib.auth.forms import UserChangeForm, UserCreationForm, AuthenticationForm

  new_help_text = UserChangeForm.base_fields['username'].help_text.replace('30', '100')

  for form in [UserChangeForm, UserCreationForm, AuthenticationForm]:
    form.base_fields['username'].max_length = 100
    form.base_fields['username'].widget.attrs['maxlength'] = 100
    form.base_fields['username'].validators[0].limit_value = 100
    form.base_fields['username'].help_text = new_help_text

if User._meta.get_field("username").max_length != 100:
  patch_user_model(User)
