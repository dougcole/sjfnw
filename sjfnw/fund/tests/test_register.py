import logging

from django.core.urlresolvers import reverse

from sjfnw.fund import models
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')

class Register(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.fund_register')

  def test_load(self):
    response = self.client.get(self.url, follow=True)

    self.assertTemplateUsed(response, 'fund/register.html')
    self.assertEqual(response.context['error_msg'], '', msg='Error message is blank on load')

  def test_post_blank(self):
    response = self.client.post(self.url, {
      'first_name': u'',
      'last_name': u'',
      'password': u'',
      'passwordtwo': u'',
      'email': u'',
      'giving_project': u''
      }, follow=True)

    self.assertTemplateUsed(response, 'fund/register.html')
    errors = response.context['form'].errors
    self.assertIn('first_name', errors, msg='Error for first_name')
    self.assertIn('last_name', errors, msg='Error for last_name')
    self.assertIn('email', errors, msg='Error for email')
    self.assertIn('password', errors, msg='Error for password')
    self.assertIn('passwordtwo', errors, msg='Error for passwordtwo')

  def test_post_valid_no_gp(self):
    response = self.client.post(self.url, {
      'first_name': u'New',
      'last_name': u'User',
      'password': u'pwpwpw',
      'passwordtwo': u'pwpwpw',
      'email': u'newemail@gmail.com',
      'giving_project': u''
      }, follow=True)

    self.assertTemplateUsed(response, 'fund/account_projects.html')
    self.assertEqual(len(response.context['ships']), 0)

  def test_post_valid_gp(self):
    gp = models.GivingProject.objects.get(title='Pre training')

    response = self.client.post(self.url, {
      'first_name': u'New',
      'last_name': u'User',
      'password': u'pwpwpw',
      'passwordtwo': u'pwpwpw',
      'email': u'newemail@gmail.com',
      'giving_project': unicode(gp.pk)
      }, follow=True)

    self.assertTemplateUsed(response, 'fund/registered.html')
    self.assertEqual(response.context['proj'], gp)

  def test_post_valid_gp_preapproved(self):
    gp = models.GivingProject.objects.get(title='Pre training')
    gp.pre_approved = 'newemail@gmail.com'
    gp.save()

    res = self.client.post(self.url, {
      'first_name': u'New',
      'last_name': u'User',
      'password': u'pwpwpw',
      'passwordtwo': u'pwpwpw',
      'email': u'newemail@gmail.com',
      'giving_project': unicode(gp.pk)
    }, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/forms/add_contacts.html')
