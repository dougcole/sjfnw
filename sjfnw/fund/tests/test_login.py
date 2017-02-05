from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from sjfnw.fund.tests.base import BaseFundTestCase

class Login(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.fund_login')

  def setUp(self):
    super(Login, self).setUp()
    self.form_data = {
      'email': u'',
      'password': u''
    }

  def test_get(self):
    response = self.client.get(self.url, follow=True)

    self.assertTemplateUsed(response, 'fund/login.html')

  def test_missing_fields(self):
    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/login.html')

    errors = response.context['form'].errors
    self.assertRegexpMatches(errors['email'][0], 'required')
    self.assertRegexpMatches(errors['password'][0], 'required')
    self.assertEqual(response.context['error_msg'], u'')

  def test_not_registered(self):
    self.form_data['email'] = 'valid@email.com'
    self.form_data['password'] = 'apassword'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/login.html')

    errors = response.context['form'].errors
    self.assertEqual(len(errors), 0)
    self.assertRegexpMatches(response.context['error_msg'], 'match')

  def test_invalid_email(self):
    self.form_data['email'] = 'username'
    self.form_data['password'] = 'apassword'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/login.html')

    errors = response.context['form'].errors
    self.assertRegexpMatches(errors['email'][0], 'Enter a valid email')

  def test_user_only(self):
    User.objects.create_user('login@email.com', 'login@email.com', 'password')

    self.form_data['email'] = 'login@email.com'
    self.form_data['password'] = 'password'

    res = self.client.post(self.url, self.form_data)

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, self.BASE_URL + reverse('sjfnw.fund.views.not_member'))
