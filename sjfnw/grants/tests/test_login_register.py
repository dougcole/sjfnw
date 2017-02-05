import logging

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.constants import FORM_ERRORS
from sjfnw.grants.models import Organization

logger = logging.getLogger('sjfnw')


class Login(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.org_login')

  def test_get(self):
    response = self.client.get(self.url, follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_login_register.html')

  def test_not_registered(self):
    form_data = {
      'email': 'askdhjhakjs@jhasd.com',
      'password': 'apassworD'
    }

    response = self.client.post(self.url, form_data, follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_login_register.html')
    self.assert_message(response, 'Your password didn\'t match the one on file. Please try again.')

  def test_wrong_pw(self):
    Organization.objects.create_with_user(email='a@b.com', password='abc', name='ABC')
    form_data = {
      'email': 'a@b.com',
      'password': 'wrong!'
    }

    response = self.client.post(self.url, form_data, follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_login_register.html')
    self.assert_message(response, 'Your password didn\'t match the one on file. Please try again.')

  def test_valid(self):
    Organization.objects.create_with_user(email='a@b.com', password='abc', name='ABC')
    form_data = {
      'email': 'a@b.com',
      'password': 'abc'
    }

    response = self.client.post(self.url, form_data, follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_home.html')

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

    response = self.client.post(self.url, registration, follow=True)

    self.assertTemplateUsed(response, self.template_success)
    self.assert_count(Organization.objects.filter(name='Unique, New York'), 1)
    self.assert_count(User.objects.filter(username='uniquenewyork@gmail.com'), 1)

  def test_repeat_org_name(self):
    """ Verify that registration fails if org with same org name and some user is already in DB.
        Name matches an existing org (email doesn't) """
    registration = {
        'email': 'uniquenewyork@gmail.com',
        'password': 'one',
        'passwordtwo': 'one',
        'organization': 'officemax foundation'
    }
    self.assert_count(User.objects.filter(username='uniquenewyork@gmail.com'), 0)

    # Make sure matching org has another user associated with it
    org = Organization.objects.get(name='OfficeMax Foundation')
    org.user = User.objects.create_user('a@fake.com', 'b@fake.com', 'password')
    org.save()

    response = self.client.post(self.url, registration, follow=True)

    self.assertTemplateUsed(response, self.template_error)
    self.assertFormError(response, 'register', None, FORM_ERRORS['org_registered'])
    self.assert_count(Organization.objects.filter(name='OfficeMax Foundation'), 1)
    self.assert_count(User.objects.filter(username='uniquenewyork@gmail.com'), 0)

  def test_repeat_org_email(self):
    """ Email matches an existing org (name doesn't) """
    registration = {
        'email': 'neworg@gmail.com',
        'password': 'one',
        'passwordtwo': 'one',
        'organization': 'Brand New'
    }

    self.assertEqual(1, Organization.objects.filter(user__username='neworg@gmail.com').count())
    self.assertEqual(0, Organization.objects.filter(name='Brand New').count())

    response = self.client.post(self.url, registration, follow=True)

    self.assertEqual(1, Organization.objects.filter(user__username='neworg@gmail.com').count())
    self.assertEqual(0, Organization.objects.filter(name='Brand New').count())
    self.assertTemplateUsed(response, self.template_error)
    self.assertFormError(response, 'register', None, FORM_ERRORS['email_registered'])

  def test_repeat_user_email(self):
    """ Email matches a user, but email/name don't match an org """
    User.objects.create_user('bababa@gmail.com', 'bababa@gmail.com', 'noob')

    registration = {
        'email': 'bababa@gmail.com',
        'password': 'one',
        'passwordtwo': 'one',
        'organization': 'Brand New'
    }

    self.assert_count(User.objects.filter(username='bababa@gmail.com'), 1)
    self.assert_count(Organization.objects.filter(name='Brand New'), 0)
    self.assert_count(Organization.objects.filter(user__username='bababa@gmail.com'), 0)

    response = self.client.post(self.url, registration, follow=True)

    self.assert_count(Organization.objects.filter(name='Brand New'), 0)
    self.assertTemplateUsed(response, self.template_error)
    self.assertFormError(response, 'register', None, FORM_ERRORS['email_registered_pc'])

  def test_admin_entered_match(self):
    """ Org name matches an org that was entered by staff (has no user) """

    org = Organization(name='Ye olde Orge')
    org.save()
    self.assert_count(User.objects.filter(username='bababa@gmail.com'), 0)

    registration = {
      'email': 'bababa@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': 'Ye olde Orge'
    }
    response = self.client.post(self.url, registration, follow=True)

    user = User.objects.get(username='bababa@gmail.com')
    self.assertEqual(user.is_active, False)
    org.refresh_from_db()
    self.assertEqual(org.user, user)

    self.assertTemplateUsed(response, self.template_error)
    self.assert_message(response, ('You have registered successfully but your '
        'account needs administrator approval. Please contact '
        '<a href="mailto:info@socialjusticefund.org">info@socialjusticefund.org</a>'))
