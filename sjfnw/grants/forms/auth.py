from django import forms
from django.core.exceptions import ValidationError

class LoginForm(forms.Form):
  email = forms.EmailField(max_length=255)
  password = forms.CharField(widget=forms.PasswordInput())


class RegisterForm(forms.Form):
  email = forms.EmailField(max_length=255)
  password = forms.CharField(widget=forms.PasswordInput())
  passwordtwo = forms.CharField(widget=forms.PasswordInput(), label='Re-enter password')
  organization = forms.CharField()

  def clean(self):
    cleaned_data = super(RegisterForm, self).clean()
    org = cleaned_data.get('organization')
    email = cleaned_data.get('email')

    if org and email:
      error_msg = Organization.check_registration(org, email)
      if error_msg:
        raise ValidationError(error_msg)

      password = cleaned_data.get('password')
      passwordtwo = cleaned_data.get('passwordtwo')
      if password and passwordtwo and password != passwordtwo:
        raise ValidationError('Passwords did not match.')

    return cleaned_data
