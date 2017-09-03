import logging

from django.core.urlresolvers import reverse

from sjfnw.fund import models, views
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')

class AddEstimates(BaseFundTestCase):

  get_url = reverse('fund:home')
  post_url = reverse('fund:add_estimates')

  def setUp(self):
    super(AddEstimates, self).setUp()
    self.login_as_member('new')

    # use post training project to require estimates
    membership = models.Membership.objects.get(member_id=self.member_id,
                                               giving_project_id=self.post_id)
    member = models.Member.objects.get(pk=self.member_id)
    member.current = membership.pk
    member.save()

    # create donors without estimates
    donor = models.Donor(firstname='Al', lastname='Bautista', membership=membership)
    donor.save()
    self.donor_id1 = donor.pk
    donor = models.Donor(firstname='Velcro', lastname='Cat', membership=membership)
    donor.save()
    self.donor_id2 = donor.pk

    # set up base form POST data given 2 donors we just created
    self.base_form_data = {
      'form-MAX_NUM_FORMS': 2,
      'form-INITIAL_FORMS': 2,
      'form-TOTAL_FORMS': 2,
      'form-0-donor': unicode(self.donor_id1),
      'form-0-amount': u'',
      'form-0-likelihood': u'',
      'form-1-donor': unicode(self.donor_id2),
      'form-1-amount': u'',
      'form-1-likelihood': u'',
    }

  def test_home_shows_estimates_form(self):

    response = self.client.get(self.get_url, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_estimates.html')
    formset = response.context['formset']
    self.assertEqual(len(formset), 2)

  def test_post_empty_form(self):
    response = self.client.post(self.post_url, self.base_form_data, follow=True)

    # verify same template is used, with errors for both fields
    self.assertTemplateUsed(response, 'fund/forms/add_estimates.html')
    errors = response.context['formset'].errors
    for i in range(0, 2):
      self.assertEqual(errors[i]['amount'], [u'This field is required.'])
      self.assertEqual(errors[i]['likelihood'], [u'This field is required.'])

  def test_partial_form(self):
    # fill out one of the forms
    form_data = self.base_form_data.copy()
    form_data['form-0-amount'] = u'200'
    form_data['form-0-likelihood'] = u'30'

    response = self.client.post(self.post_url, form_data, follow=True)

    # verify same template used, with errors for empty form
    self.assertTemplateUsed(response, 'fund/forms/add_estimates.html')
    errors = response.context['formset'].errors
    self.assertEqual(errors[0], {})
    self.assertEqual(errors[1]['amount'], [u'This field is required.'])
    self.assertEqual(errors[1]['likelihood'], [u'This field is required.'])

    # verify donor not updated
    donor = models.Donor.objects.get(pk=self.donor_id2)
    self.assertEqual(donor.amount, None)
    self.assertEqual(donor.likelihood, None)

  def test_success(self):
    # fill out both forms
    form_data = self.base_form_data.copy()
    form_data['form-0-amount'] = u'200'
    form_data['form-0-likelihood'] = u'30'
    form_data['form-1-amount'] = u'500'
    form_data['form-1-likelihood'] = u'10'

    response = self.client.post(self.post_url, form_data, follow=True)

    # verify json response
    self.assertEqual(response.content, 'success')

    # verify donors updated
    donor = models.Donor.objects.get(pk=self.donor_id1)
    self.assertEqual(donor.amount, 200)
    self.assertEqual(donor.likelihood, 30)
    donor = models.Donor.objects.get(pk=self.donor_id2)
    self.assertEqual(donor.amount, 500)
    self.assertEqual(donor.likelihood, 10)

  def test_invalid_input(self):
    # fill out both forms, but with invalid values
    form_data = self.base_form_data.copy()
    form_data['form-0-amount'] = u'something'
    form_data['form-0-likelihood'] = u'1.5'
    form_data['form-1-amount'] = u'-20'
    form_data['form-1-likelihood'] = u'110'

    response = self.client.post(self.post_url, form_data, follow=True)

    # verify same template used, with errors for empty form
    self.assertTemplateUsed(response, 'fund/forms/add_estimates.html')

    # verify expected errors
    errors = response.context['formset'].errors
    self.assertRegexpMatches(errors[0]['amount'][0], 'Enter a whole number')
    self.assertRegexpMatches(errors[0]['likelihood'][0], 'Enter a whole number')
    self.assertRegexpMatches(errors[1]['amount'][0], 'Must be greater than')
    self.assertRegexpMatches(errors[1]['likelihood'][0], 'Ensure this value is less than')
