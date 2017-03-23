import logging

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from sjfnw.grants import views
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.constants import FORM_ERRORS
from sjfnw.grants.models import Organization

logger = logging.getLogger('sjfnw')


class Login(BaseGrantTestCase):

  url = reverse(views.org_login)

  def test_get(self):
    res = self.client.get(self.url, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_login_register.html')

  def test_not_registered(self):
    form_data = {
      'email': 'askdhjhakjs@jhasd.com',
      'password': 'apassworD'
    }

    res = self.client.post(self.url, form_data, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_login_register.html')
    self.assert_message(res, 'Your password didn\'t match the one on file. Please try again.')

  def test_wrong_pw(self):
    Organization.objects.create_with_user(email='a@b.com', password='abc', name='ABC')
    form_data = {
      'email': 'a@b.com',
      'password': 'wrong!'
    }

    res = self.client.post(self.url, form_data, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_login_register.html')
    self.assert_message(res, 'Your password didn\'t match the one on file. Please try again.')

  def test_valid(self):
    Organization.objects.create_with_user(email='a@b.com', password='abc', name='ABC')
    form_data = {
      'email': 'a@b.com',
      'password': 'abc'
    }

    res = self.client.post(self.url, form_data, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_home.html')

class Register(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.org_register')
  template_success = 'grants/org_home.html'
  template_error = 'grants/org_login_register.html'

  def test_valid_registration(self):
    """ All fields provided, neither email nor name match an org in db """
    registration = {
      'email': 'uniquenewyork@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': 'Unique, New York'
      }

    self.assert_count(Organization.objects.filter(name='Unique, New York'), 0)
    self.assert_count(User.objects.filter(username='uniquenewyork@gmail.com'), 0)

    res = self.client.post(self.url, registration, follow=True)

    self.assertTemplateUsed(res, self.template_success)
    self.assert_count(Organization.objects.filter(name='Unique, New York'), 1)
    self.assert_count(User.objects.filter(username='uniquenewyork@gmail.com'), 1)

  def test_repeat_org_name(self):
    """ Verify that registration fails if org with same org name and some user is already in DB. """
    existing_org = factories.Organization()
    registration = {
        'email': 'uniquenewyork@gmail.com',
        'password': 'one',
        'passwordtwo': 'one',
        'organization': existing_org.name
    }
    self.assert_count(User.objects.filter(username=registration['email']), 0)

    res = self.client.post(self.url, registration, follow=True)

    self.assertTemplateUsed(res, self.template_error)
    self.assertFormError(res, 'register', None, FORM_ERRORS['org_registered'])
    self.assert_count(User.objects.filter(username=registration['email']), 0)

  def test_repeat_org_email(self):
    """ Email matches an existing org (name doesn't) """
    existing_org = factories.Organization()
    registration = {
        'email': existing_org.user.username,
        'password': 'one',
        'passwordtwo': 'one',
        'organization': 'Brand New'
    }

    self.assert_count(Organization.objects.filter(name=registration['organization']), 0)

    res = self.client.post(self.url, registration, follow=True)

    self.assert_count(Organization.objects.filter(name=registration['organization']), 0)
    self.assertTemplateUsed(res, self.template_error)
    self.assertFormError(res, 'register', None, FORM_ERRORS['email_registered'])

  def test_repeat_user_email(self):
    """ Email matches a user, but email/name don't match an org """
    User.objects.create_user('bababa@gmail.com', 'bababa@gmail.com', 'bb')

    registration = {
        'email': 'bababa@gmail.com',
        'password': 'one',
        'passwordtwo': 'one',
        'organization': 'Brand New'
    }

    self.assert_count(Organization.objects.filter(name=registration['organization']), 0)
    self.assert_count(Organization.objects.filter(user__username=registration['email']), 0)

    res = self.client.post(self.url, registration, follow=True)

    self.assert_count(Organization.objects.filter(name=registration['organization']), 0)
    self.assertTemplateUsed(res, self.template_error)
    self.assertFormError(res, 'register', None, FORM_ERRORS['email_registered_pc'])

  def test_admin_entered_match(self):
    """ Org name matches an org that was entered by staff (has no user) """

    org = Organization(name='Ye olde Orge')
    org.save()

    registration = {
      'email': 'bababa@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': org.name
    }
    res = self.client.post(self.url, registration, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, self.template_error)
    self.assert_message(res, ('You have registered successfully but your '
        'account needs administrator approval. Please contact '
        '<a href="mailto:info@socialjusticefund.org">info@socialjusticefund.org</a>'))

    user = User.objects.get(username=registration['email'])
    self.assertFalse(user.is_active)
    org.refresh_from_db()
    self.assertEqual(org.user, user)

