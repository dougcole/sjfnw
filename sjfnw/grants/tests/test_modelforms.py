import json

from django.forms import ValidationError
from django.forms.utils import ErrorList

from sjfnw.grants import constants as gc
from sjfnw.grants.modelforms import (StandardApplicationForm,
    SeedApplicationForm, RapidResponseApplicationForm, get_form_for_cycle)
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase

ERR_REQUIRED = 'This field is required.'
FULL_CHOICES_LENGTH = len(gc.STATUS_CHOICES) + 1 # 1 empty

class GrantApplicationTypes(BaseGrantTestCase):
  
  def test_get_form(self):
    cycle = factories.GrantCycle()
    self.assertEqual(get_form_for_cycle(cycle), 'standard')

    cycle = factories.GrantCycle(title='Rapid Response Cycle')
    self.assertEqual(get_form_for_cycle(cycle), 'rapid')

    cycle = factories.GrantCycle(title='Seed Grants')
    self.assertEqual(get_form_for_cycle(cycle), 'seed')

  def test_standard_requirements(self):
    cycle = factories.GrantCycle()
    form = StandardApplicationForm(cycle, {})

    self.assert_length(form.fields['status'].choices, FULL_CHOICES_LENGTH - 1)

    self.assertFalse(form.is_valid())
    for field in ['budget1', 'budget2', 'budget3', 'demographics', 'funding_sources']:
      self.assertTrue(field in form.errors, 'Expected form error for {}'.format(field))
      err = form.errors[field]
      self.assertIsInstance(err, ErrorList)
      self.assertRegexpMatches(err.as_text(), ERR_REQUIRED)

  def test_rapid(self):
    cycle = factories.GrantCycle(title='Rapid Response')
    form = RapidResponseApplicationForm(cycle, {})

    self.assert_length(form.fields['status'].choices, FULL_CHOICES_LENGTH)

    self.assertFalse(form.is_valid())
    self.assertIn('demographics', form.errors)
    self.assertRegexpMatches(form.errors['demographics'].as_text(), ERR_REQUIRED)
    for field in ['budget1', 'budget2', 'budget3', 'funding_sources']:
      self.assertNotIn(field, form.errors)

  def test_seed(self):
    cycle = factories.GrantCycle(title='Seed Cycle')
    form = SeedApplicationForm(cycle, {})

    self.assert_length(form.fields['status'].choices, FULL_CHOICES_LENGTH)

    self.assertFalse(form.is_valid())
    for field in ['budget1', 'budget2', 'budget3', 'funding_sources', 'demographics']:
      self.assertNotIn(field, form.errors)

class GrantApplicationTimeline(BaseGrantTestCase):

  def setUp(self):
    cycle = factories.GrantCycle()
    self.form = StandardApplicationForm(cycle)

  def test_invalid_empty(self):
    timeline = ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
    self.form.cleaned_data = {'timeline': json.dumps(timeline)}

    self.assertRaisesRegexp(ValidationError, ERR_REQUIRED, self.form.clean_timeline)

  def test_invalid_incomplete(self):
    timeline = ['Jan', 'Chillin', 'Not applicable',
               'Feb', 'Petting dogs', '5 dogs',
               'Mar', '', 'Sprouts',
               'July', '', '',
               '', 'Reading in the shade', 'No sunburns']
    self.form.cleaned_data = {'timeline': json.dumps(timeline)}

    self.assertRaisesRegexp(ValidationError,
      'All three columns are required for each quarter that you include in your timeline.',
      self.form.clean_timeline)

  def test_valid_single_row(self):
    timeline = ['Jan', 'Chillin', 'Not applicable',
               '', '', '', '', '', '', '', '', '', '', '', '']
    self.form.cleaned_data = {'timeline': json.dumps(timeline)}

    # should not raise exception
    self.form.clean_timeline()

  def test_valid_full_five_qtr(self):
    timeline = [
      'Jan', 'Chillin', 'Not applicable',
      'Feb', 'Petting dogs', '5 dogs',
      'Mar', 'Planting daffodils', 'Sprouts',
      'July', 'Walking around Greenlake', '9 times',
      'August', 'Reading in the shade', 'No sunburns'
    ]

    self.form.cleaned_data = {'timeline': json.dumps(timeline)}

    # should not raise exception
    self.form.clean_timeline()

class GrantApplicationCollabRefs(BaseGrantTestCase):

  def setUp(self):
    cycle = factories.GrantCycle()
    self.form = StandardApplicationForm(cycle)

  def test_valid(self):
    collab_refs = [
      {'name': 'Alice', 'org': 'HJF', 'phone': '5556708', 'email': ''},
      {'name': 'Prol', 'org': 'Abc', 'phone': '', 'email': 'fake@fake.com'}
    ]

    self.form.cleaned_data = {'collaboration_references': json.dumps(collab_refs)}

    self.form.clean_collaboration_references()

  def test_invalid_empty(self):
    collab_refs = [
      {'name': '', 'org': '', 'phone': '', 'email': ''},
      {'name': '', 'org': '', 'phone': '', 'email': ''}
    ]

    self.form.cleaned_data = {'collaboration_references': json.dumps(collab_refs)}

    self.assertRaisesRegexp(ValidationError,
        '',
        self.form.clean_collaboration_references)

class GrantApplicationRJRefs(BaseGrantTestCase):

  def setUp(self):
    cycle = factories.GrantCycle()
    self.form = StandardApplicationForm(cycle)

  def test_invalid_partial(self):
    rj_refs = [
      {'name': 'Alice', 'org': 'HJF', 'phone': '5556708', 'email': ''},
      {'name': 'Prol', 'org': '', 'phone': '', 'email': 'fake@fake.com'}
    ]

    self.form.cleaned_data = {'racial_justice_references': json.dumps(rj_refs)}

    self.assertRaisesRegexp(ValidationError,
      'Please include a name, organization, and phone or email for each reference you include.',
      self.form.clean_racial_justice_references)

  def test_valid(self):
    rj_refs = [
      {'name': 'Alice', 'org': 'HJF', 'phone': '5556708', 'email': ''},
      {'name': 'Prol', 'org': 'Abc', 'phone': '', 'email': 'fake@fake.com'}
    ]

    self.form.cleaned_data = {'racial_justice_references': json.dumps(rj_refs)}

    self.form.clean_racial_justice_references()

  def test_valid_empty(self):
    rj_refs = [
      {'name': '', 'org': '', 'phone': '', 'email': ''},
      {'name': '', 'org': '', 'phone': '', 'email': ''}
    ]

    self.form.cleaned_data = {'racial_justice_references': json.dumps(rj_refs)}

    self.form.clean_racial_justice_references()
