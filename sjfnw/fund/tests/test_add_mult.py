# encoding: utf8

from django.core.urlresolvers import reverse

from sjfnw.fund import models
from sjfnw.fund.tests.base import BaseFundTestCase

class AddMultipleDonorsPre(BaseFundTestCase):

  url = reverse('fund:add_contacts')

  def setUp(self):
    super(AddMultipleDonorsPre, self).setUp()
    self.login_as_member('new')
    self.form_data = {
      'form-TOTAL_FORMS': u'5',
      'form-INITIAL_FORMS': u'0',
      'form-MAX_NUM_FORMS': u'1000'
    }
    for i in range(0, 5):
      self.form_data['form-%d-firstname' % i] = u''
      self.form_data['form-%d-lastname' % i] = u''

  def test_get(self):
    # note: get via home is covered in home tests
    response = self.client.get(self.url, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')

  def test_post_empty(self):
    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')
    error = response.context['empty_error']
    self.assertRegexpMatches(error, 'enter at least one contact')

  def test_post_first_name(self):
    self.form_data['form-0-firstname'] = u'First'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertEqual(response.content, 'success')

    donors = models.Donor.objects.filter(membership_id=self.pre_id)
    self.assertEqual(len(donors), 1)
    self.assertEqual(donors[0].firstname, 'First')

  def test_post_multiple_valid(self):
    self.form_data['form-0-firstname'] = u'First'
    self.form_data['form-1-firstname'] = u'Seattle'
    self.form_data['form-1-lastname'] = u'Washington'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertEqual(response.content, 'success')

    donors = models.Donor.objects.filter(membership_id=self.pre_id).order_by('firstname')
    self.assertEqual(len(donors), 2)

    self.assertEqual(donors[0].firstname, u'First')
    self.assertEqual(donors[0].lastname, u'')

    self.assertEqual(donors[1].firstname, u'Seattle')
    self.assertEqual(donors[1].lastname, u'Washington')

  def test_post_multiple_invalid(self):
    self.form_data['form-0-lastname'] = u'Last'

    self.form_data['form-1-firstname'] = u'Seattle'
    self.form_data['form-1-lastname'] = u'Washington'

    self.form_data['form-3-lastname'] = u'Smith'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')

    errors = response.context['formset'].errors
    self.assertRegexpMatches(errors[0]['firstname'][0], 'required')
    self.assertEqual(errors[1], {})
    self.assertEqual(errors[2], {})
    self.assertRegexpMatches(errors[3]['firstname'][0], 'required')

    donors = models.Donor.objects.filter(membership_id=self.pre_id)
    self.assertEqual(len(donors), 0)

class AddMultipleDonorsPost(BaseFundTestCase):

  url = reverse('fund:add_contacts')

  def setUp(self):
    super(AddMultipleDonorsPost, self).setUp()
    self.login_as_member('new')

    # use post fundraising training membership
    member = models.Member.objects.get(pk=self.member_id)
    member.current = self.post_id
    member.save()

    self.form_data = {
      'form-TOTAL_FORMS': u'5',
      'form-INITIAL_FORMS': u'0',
      'form-MAX_NUM_FORMS': u'1000'
    }
    for i in range(0, 5):
      self.form_data['form-%d-firstname' % i] = u''
      self.form_data['form-%d-lastname' % i] = u''
      self.form_data['form-%d-amount' % i] = u''
      self.form_data['form-%d-likelihood' % i] = u''

  def test_get(self):
    # note: get via home is covered in home tests
    response = self.client.get(self.url, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')

  def test_post_empty(self):
    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')
    error = response.context['empty_error']
    self.assertRegexpMatches(error, 'enter at least one contact')

    donors = models.Donor.objects.filter(membership_id=self.post_id)
    self.assertEqual(len(donors), 0)

  def test_post_first_name(self):
    self.form_data['form-0-firstname'] = u'First'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')

    errors = response.context['formset'].errors
    self.assertRegexpMatches(errors[0]['amount'][0], 'required')
    self.assertRegexpMatches(errors[0]['likelihood'][0], 'required')
    self.assertEqual(errors[1], {})

    donors = models.Donor.objects.filter(membership_id=self.post_id)
    self.assertEqual(len(donors), 0)

  def test_post_multiple_valid(self):
    self.form_data['form-0-firstname'] = u'Fürst'
    self.form_data['form-0-amount'] = u'40'
    self.form_data['form-0-likelihood'] = u'90'
    self.form_data['form-1-firstname'] = u'ﭯﮃﭺ۹'
    self.form_data['form-1-lastname'] = u'ฃจฬษ'
    self.form_data['form-1-amount'] = u'4000.50'
    self.form_data['form-1-likelihood'] = u'45'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertEqual(response.content, 'success')

    donors = models.Donor.objects.filter(membership_id=self.post_id).order_by('amount')
    self.assertEqual(len(donors), 2)
    self.assertEqual(donors[0].firstname, u'Fürst')
    self.assertEqual(donors[0].lastname, u'')
    self.assertEqual(donors[0].amount, 40)
    self.assertEqual(donors[0].likelihood, 90)
    self.assertEqual(donors[1].firstname, u'ﭯﮃﭺ۹')
    self.assertEqual(donors[1].lastname, u'ฃจฬษ')
    self.assertEqual(donors[1].amount, 4000)
    self.assertEqual(donors[1].likelihood, 45)

  def test_post_multiple_invalid(self):
    self.form_data['form-0-lastname'] = 'Last'
    self.form_data['form-0-amount'] = u'0'
    self.form_data['form-0-likelihood'] = u''

    self.form_data['form-1-firstname'] = 'Seattle'
    self.form_data['form-1-lastname'] = 'Washington'
    self.form_data['form-1-amount'] = u'500.50'
    self.form_data['form-1-likelihood'] = u'120'

    self.form_data['form-3-lastname'] = 'Smith'
    self.form_data['form-3-amount'] = u'-5'
    self.form_data['form-3-likelihood'] = u'-20'

    response = self.client.post(self.url, self.form_data, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')

    errors = response.context['formset'].errors

    self.assertRegexpMatches(errors[0]['firstname'][0], 'required')
    self.assertRegexpMatches(errors[0]['likelihood'][0], 'required')

    self.assertRegexpMatches(errors[1]['likelihood'][0], 'less than')

    self.assertEqual(errors[2], {})

    self.assertRegexpMatches(errors[3]['firstname'][0], 'required')
    self.assertRegexpMatches(errors[3]['amount'][0], 'greater than')
    self.assertRegexpMatches(errors[3]['likelihood'][0], 'greater than')

    donors = models.Donor.objects.filter(membership_id=self.post_id)
    self.assertEqual(len(donors), 0)
