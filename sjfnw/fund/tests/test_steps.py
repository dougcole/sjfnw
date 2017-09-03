from datetime import timedelta
import logging
import unittest

from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.fund.models import Donor, Step, Membership
from sjfnw.fund.modelforms import StepForm
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')

class AddStep(BaseFundTestCase):

  def setUp(self):
    super(AddStep, self).setUp()
    self.login_as_member('new')
    donor = Donor(firstname='user', lastname='', membership_id=self.pre_id)
    donor.save()
    self.donor_id = donor.pk
    self.url = reverse('fund:add_step', kwargs={'donor_id': donor.pk})
    self.valid_form = {
      'date': '11/13/2034',
      'description': 'Talk to them'
    }

  def test_get(self):
    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/forms/add_step.html')
    self.assertIsInstance(res.context['form'], StepForm)

  def test_blank(self):
    form_data = {
      'date': u'',
      'description': u''
    }
    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/forms/add_step.html')

  def test_missing_date(self):
    form_data = {
      'date': u'',
      'description': 'Talk to them'
    }
    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/forms/add_step.html')
    self.assertFormError(response, 'form', 'date', 'This field is required.')

  def test_missing_desc(self):
    form_data = {
      'date': '11/13/2034',
      'description': ''
    }
    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/forms/add_step.html')
    self.assertFormError(response, 'form', 'description', 'This field is required.')

  def test_valid(self):
    response = self.client.post(self.url, self.valid_form)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.content, 'success')
    step = Step.objects.get(donor_id=self.donor_id)
    self.assertEqual(step.description, 'Talk to them')

  def test_invalid_donor(self):
    url = reverse('fund:add_step', kwargs={'donor_id': 0})
    response = self.client.post(url, self.valid_form)
    self.assertEqual(response.status_code, 404)

  def test_has_next_step(self):
    step = Step(donor_id=self.donor_id, date='2042-11-14',
                       description='Meet for coffee')
    step.save()
    response = self.client.post(self.url, self.valid_form)
    self.assertEqual(response.status_code, 400)
    self.assertEqual(Step.objects.filter(donor_id=self.donor_id).count(), 1)


class EditStep(BaseFundTestCase):

  def setUp(self):
    super(EditStep, self).setUp()
    self.login_as_member('new')
    donor = Donor(firstname='user', lastname='', membership_id=self.pre_id)
    donor.save()
    self.donor_id = donor.pk
    step = Step(donor_id=donor.pk, date='2034-11-13', description='Think about it')
    step.save()
    self.step_id = step.pk
    self.url = reverse('fund:edit_step',
                       kwargs={'donor_id': donor.pk, 'step_id': step.pk})
    self.valid_form = {
      'date': '11/13/2034',
      'description': 'Talk to them'
    }

  def test_blank(self):
    form_data = {
      'date': u'',
      'description': u''
    }
    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/forms/edit_step.html')

  def test_missing_date(self):
    form_data = {
      'date': u'',
      'description': 'Talk to them'
    }
    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/forms/edit_step.html')
    self.assertFormError(response, 'form', 'date', 'This field is required.')

  def test_missing_desc(self):
    form_data = {
      'date': '11/13/2034',
      'description': ''
    }
    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/forms/edit_step.html')
    self.assertFormError(response, 'form', 'description', 'This field is required.')

  def test_valid(self):
    response = self.client.post(self.url, self.valid_form)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.content, 'success')
    step = Step.objects.get(pk=self.step_id)
    self.assertEqual(step.description, 'Talk to them')

  def test_invalid_donor(self):
    url = reverse('fund:edit_step',
                  kwargs={'donor_id': 0, 'step_id': self.step_id})
    response = self.client.post(url, self.valid_form)
    self.assertEqual(response.status_code, 404)

  def test_invalid_step(self):
    url = reverse('fund:edit_step',
                  kwargs={'donor_id': self.donor_id, 'step_id': 0})
    response = self.client.post(url, self.valid_form)
    self.assertEqual(response.status_code, 404)


class StepComplete(BaseFundTestCase):
  """ Tests various scenarios of step completion """

  def setUp(self):
    super(StepComplete, self).setUp()
    self.login_as_member('current')
    self.url = reverse('fund:complete_step', kwargs={
      'donor_id': self.donor_id, 'step_id': self.step_id
    })
    # start with blank/defaults form
    self.form_data = {
      'asked': 'on',
      'response': 2,
      'promised_amount': '',
      'last_name': '',
      'email': '',
      'phone': '',
      'notes': '',
      'next_step': '',
      'next_step_date': '',
      'likely_to_join': '',
      'match_expected': '',
      'match_company': ''
    }

  def add_followup(self):
    """ Add valid promise followup data to self.form_data (helper, not a test) """

    self.form_data['last_name'] = 'Sozzity'
    self.form_data['email'] = 'blah@gmail.com'
    self.form_data['promise_reason'] = ['Social justice']
    self.form_data['likely_to_join'] = 1

  def test_minimal_completion(self):
    """ Verify that step can be completed without any additional input """

    # make sure step is not already completed and ask has not been recorded
    step = Step.objects.get(pk=self.step_id)
    self.assertIsNone(step.completed)

    response = self.client.post(self.url, self.form_data)
    self.assertEqual(response.content, 'success')

    step = Step.objects.get(pk=self.step_id)
    self.assertIsNotNone(step.completed)

  def test_minimal_asked(self):
    """ Verify that an ask can be entered without any other info """

    donor = Donor.objects.get(pk=self.donor_id)
    step = Step.objects.get(pk=self.step_id)

    # make sure step is not already completed and ask has not been recorded
    self.assertIsNone(step.completed)
    self.assertFalse(step.asked)
    self.assertFalse(donor.asked)

    self.form_data['asked'] = 'on'

    response = self.client.post(self.url, self.form_data)
    self.assertEqual(response.content, 'success')

    step = Step.objects.get(pk=self.step_id)
    donor = Donor.objects.get(pk=self.donor_id)

    self.assertIsNotNone(step.completed)
    self.assertTrue(step.asked)
    self.assertTrue(donor.asked)

  def test_minimal_next(self):
    """ Verify success of blank form with a next step """

    form_data = {
        'asked': '',
        'response': 2,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': 'A BRAND NEW STEP',
        'next_step_date': '2013-01-25'
    }

    pre_count = Step.objects.count()

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, 'success')

    old_step = Step.objects.get(pk=self.step_id)
    self.assertIsNotNone(old_step.completed)
    self.assertEqual(pre_count + 1, Step.objects.count())
    self.assertEqual(1, Step.objects.filter(description='A BRAND NEW STEP').count())

  @unittest.skip('Incomplete')
  def test_valid_response(self):
    """ TO DO
    contact that was already asked
    add a response
    make sure step.asked stays false """
    pass

  def post_and_verify_followup_saved(self, form_data):
    """ Posts the form and verifies success without follow up info saved appropriately

      Not a test in itself - used by valid follow up tests
    """

    pre_donor = Donor.objects.get(pk=self.donor_id)

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, 'success')

    promised = form_data['promised_amount']
    if promised == '5,000': # hacky workaround
      promised = 5000

    # get donor and step after the POST
    donor = Donor.objects.get(pk=self.donor_id)
    step = Step.objects.get(pk=self.step_id)

    # step completion, asked update
    self.assertTrue(donor.asked)
    self.assertTrue(step.asked)
    self.assertIsNotNone(step.completed)

    # follow up info
    if form_data['response'] == 1:
      self.assertEqual(donor.lastname, form_data['last_name'])
      self.assertEqual(donor.email, form_data['email'])
      self.assertEqual(donor.phone, form_data['phone'])
      self.assertEqual(donor.promised, promised)
      self.assertEqual(step.promised, promised)
      if form_data['match_expected'] or form_data['match_company']:
        self.assertEqual(donor.match_expected, form_data['match_expected'])
        self.assertEqual(donor.match_company, form_data['match_company'])
      else:
        self.assertEqual(donor.match_expected, 0)
        self.assertEqual(donor.match_company, '')
    else:
      if form_data['response'] == 3: # declined
        self.assertEqual(donor.promised, 0)
        self.assertEqual(step.promised, 0)
      else:
        self.assertEqual(donor.promised, pre_donor.promised)
        self.assertIsNone(step.promised)
      self.assertEqual(donor.lastname, pre_donor.lastname)
      self.assertEqual(donor.phone, pre_donor.phone)
      self.assertEqual(donor.email, pre_donor.email)

  def test_valid_followup(self):
    """ Success with promise amount, last name and email """

    self.form_data['asked'] = 'on'
    self.form_data['response'] = 1
    self.form_data['promised_amount'] = 50
    self.add_followup()

    self.post_and_verify_followup_saved(self.form_data)

  def test_valid_followup_comma(self):
    """ Success when promise amount has comma in it

      Test whether IntegerCommaField works
      Same as test_valid_followup except except amount = '5,000'
    """

    self.form_data['asked'] = 'on'
    self.form_data['response'] = 1
    self.form_data['promised_amount'] = '5,000'
    self.add_followup()

    self.post_and_verify_followup_saved(self.form_data)

  def test_valid_hiddendata1(self):
    """ Promise data not saved if response is undecided """

    self.form_data['asked'] = 'on'
    self.form_data['response'] = 2
    self.form_data['promised_amount'] = 50
    self.form_data['last_name'] = 'Sozzity'
    self.form_data['phone'] = '206-555-5898'

    self.post_and_verify_followup_saved(self.form_data)

  def test_valid_hiddendata2(self):
    """ Promise followup not saved if response is declined

      step.promised and donor.promised are set to 0
    """

    form_data = {
      'asked': 'on',
      'response': 3,
      'promised_amount': 50,
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''
    }

    self.post_and_verify_followup_saved(form_data)

  def test_valid_hiddendata3(self):
    """ Followup not required if promise amount is entered but response is undecided """

    form_data = {'asked': 'on',
      'response': 2,
      'promised_amount': 50,
      'last_name': '',
      'phone': '',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''}

    self.post_and_verify_followup_saved(form_data)

  def test_invalid_promise(self):
    """ Additional info is required when a promise is entered """

    form_data = {
        'asked': 'on',
        'response': 1,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': '',
        'next_step_date': ''}

    step1 = Step.objects.get(pk=self.step_id)
    donor1 = Donor.objects.get(pk=self.donor_id)

    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)

    response = self.client.post(self.url, form_data)

    self.assertTemplateUsed(response, 'fund/forms/complete_step.html')
    self.assertFormError(response, 'form', 'promised_amount', 'Enter an amount.')
    self.assertFormError(response, 'form', 'last_name', 'Enter a last name.')
    self.assertFormError(response, 'form', 'phone', 'Enter a phone number or email.')

    step1 = Step.objects.get(pk=self.step_id)
    donor1 = Donor.objects.get(pk=self.donor_id)

    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)

  def test_invalid_next(self):
    """ Form is not saved, errors are shown if next step is missing date or desc """

    form_data = {'asked': '',
        'response': 2,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': 'A step description!',
        'next_step_date': ''}

    response = self.client.post(self.url, form_data)

    self.assertTemplateUsed(response, 'fund/forms/complete_step.html')
    self.assertFormError(response, 'form', 'next_step_date', 'Enter a date in mm/dd/yyyy format.')

    step1 = Step.objects.get(pk=self.step_id)
    self.assertIsNone(step1.completed)

    form_data = {
      'asked': '',
      'response': 2,
      'promised_amount': '',
      'last_name': '',
      'notes': '',
      'next_step': '',
      'next_step_date': '2013-01-25'
    }

    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/forms/complete_step.html')
    self.assertFormError(response, 'form', 'next_step', 'Enter a description.')

    step1 = Step.objects.get(pk=self.step_id)
    self.assertIsNone(step1.completed)

  def test_match_entered(self):
    """ Match company is required if expected is given """

    self.form_data['asked'] = 'on'
    self.form_data['response'] = 1
    self.form_data['promised_amount'] = 50
    self.add_followup()
    self.form_data['match_expected'] = 100

    response = self.client.post(self.url, self.form_data)

    self.assertTemplateUsed(response, 'fund/forms/complete_step.html')
    self.assertFormError(response, 'form', 'match_company', 'Enter the employer\'s name.')

  def test_match_company(self):
    """ Match expected is required if company is given """

    self.form_data['asked'] = 'on'
    self.form_data['response'] = 1
    self.form_data['promised_amount'] = 50
    self.add_followup()
    self.form_data['match_company'] = 'Company X'

    response = self.client.post(self.url, self.form_data)

    self.assertTemplateUsed(response, 'fund/forms/complete_step.html')
    self.assertFormError(response, 'form', 'match_expected', 'Enter the amount matched.')

  def test_both_match_fields(self):
    """ Success and match info saved if both fields are entered """

    self.form_data['asked'] = 'on'
    self.form_data['response'] = 1
    self.form_data['promised_amount'] = 50
    self.add_followup()
    self.form_data['match_expected'] = 100
    self.form_data['match_company'] = 'Company X'

    self.post_and_verify_followup_saved(self.form_data)

  def test_donor_not_found(self):
    url = reverse('fund:complete_step', kwargs={
      'donor_id': 8989, 'step_id': self.step_id
    })
    res = self.client.post(url, self.form_data)

    self.assertEqual(res.status_code, 404)

  def test_step_not_found(self):
    url = reverse('fund:complete_step', kwargs={
      'donor_id': self.donor_id, 'step_id': 8989
    })
    res = self.client.post(url, self.form_data)

    self.assertEqual(res.status_code, 404)


class AddMultStep(BaseFundTestCase):

  url = reverse('fund:add_steps')

  def setUp(self):
    super(AddMultStep, self).setUp()
    self.login_as_member('current')

  def test_get_none(self):
    donor = Donor.objects.get(membership_id=self.ship_id)
    next_step = donor.get_next_step()
    self.assertIsNotNone(next_step)
    self.assertFalse(next_step.completed)

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.context['size'], 0)

  def test_get_some(self):
    donor = Donor(firstname='A', membership_id=self.ship_id)
    donor.save()
    donor = Donor(firstname='B', membership_id=self.ship_id)
    donor.save()

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.context['size'], 2)

  def test_get_over_ten(self):
    for i in range(1, 11):
      donor = Donor(firstname='Person{}'.format(i), membership_id=self.ship_id)
      donor.save()

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.context['size'], 10)

  def test_get_received(self):
    donor = Donor(firstname='A', membership_id=self.ship_id)
    donor.save()
    donor = Donor(firstname='B', membership_id=self.ship_id, received_this=25)
    donor.save()

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.context['size'], 1)

  def test_get_promised(self):
    donor = Donor(firstname='A', membership_id=self.ship_id, promised=300)
    donor.save()
    donor = Donor(firstname='B', membership_id=self.ship_id)
    donor.save()

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.context['size'], 1)

  def test_post_none(self):
    res = self.client.get(self.url)

    last_activity = Membership.objects.get(pk=self.ship_id).last_activity

    prefix = res.context['formset'].management_form.prefix
    initial = res.context['formset'].management_form.initial
    post_data = {}
    for key, value in initial.iteritems():
      post_data[prefix + '-' + key] = value

    res = self.client.post(self.url, post_data)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.content, 'success')
    self.assertNotEqual(last_activity, Membership.objects.get(pk=self.ship_id).last_activity)

  def test_post_invalid(self):
    donor_a = Donor(membership_id=self.ship_id, firstname='Taboo')
    donor_a.save()
    donor_b = Donor(membership_id=self.ship_id, firstname='Boggle')
    donor_b.save()

    date = timezone.now() + timedelta(days=5)
    form_data = {
      'form-TOTAL_FORMS': u'2',
      'form-INITIAL_FORMS': u'2',
      'form-MAX_NUM_FORMS': u'10',
      'form-0-donor': unicode(donor_a.pk),
      'form-0-date': '{:%m/%d/%y}'.format(date),
      'form-1-donor': unicode(donor_b.pk),
      'form-1-description': 'Talk'
    }
    res = self.client.post(self.url, form_data)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/forms/add_mult_step.html')
    self.assertFormsetError(res, 'formset', 0, 'description', 'This field is required.')
    self.assertFormsetError(res, 'formset', 1, 'date', 'Please enter a date in mm/dd/yyyy format.')
