import logging
from unittest import skip

from django import forms
from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.grants.forms import (AppReportForm, SponsoredAwardReportForm,
    GPGrantReportForm, OrgReportForm)
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants import models

import unicodecsv

logger = logging.getLogger('sjfnw')

class ReportingHomePage(BaseGrantTestCase):

  def setUp(self):
    self.login_as_admin()

  def test_load_page(self):
    response = self.client.get(reverse('sjfnw.grants.views.grants_report'))

    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'select id="report-type-selector"')
    self.assertContains(response, 'option value="#application-form"')
    self.assertContains(response, 'option value="#organization-form"')
    self.assertContains(response, 'option value="#giving-project-grant-form"')
    self.assertContains(response, 'option value="#sponsored-award-form"')


def fill_report_form(form, select_filters=False, select_fields=False, fmt='browse'):
  """ Shared method to create mock POST data for the given form

  Args:
    form: form instance to populate
    select_filters: True = select all filters, False = select none
    select_fields: True = select all fields, False = select none
    fmt: 'browse' or 'csv'

  Methods need to insert report type key themselves
  Set up to handle:
    boolean
    select fields
    year min & max
    organization_name & city (all other chars are blank)

  Returns:
    Dictionary that should be a valid POST submission for the given form
  """

  post_dict = {}
  for bound_field in form:
    field = bound_field.field
    name = bound_field.name

    if name.startswith('report'):
      if select_fields:
        if isinstance(field, forms.BooleanField):
          post_dict[name] = True
        elif isinstance(field, forms.MultipleChoiceField):
          post_dict[name] = [val[0] for val in field.choices]
        else:
          logger.error('Unexpected field type: ' + str(field))

    # if not a report_ field; must be a filter
    else:
      if isinstance(field, forms.BooleanField):
        post_dict[name] = True if select_filters else False
      elif isinstance(field, forms.MultipleChoiceField):
        # select top two choices (safe to assume that all multi-select have at least 2)
        post_dict[name] = [field.choices[0][0], field.choices[1][0]] if select_filters else []
      elif name.startswith('year_m'):
        # years are required fields; handle the same in either case
        post_dict[name] = 1995 if name == 'year_min' else timezone.now().year
      elif isinstance(field, forms.CharField):
        if select_filters:
          if name == 'organization_name':
            post_dict[name] = 'Foundation'
          elif name == 'city':
            post_dict[name] = 'Seattle'
        else:
          post_dict[name] = ''
      elif name == 'registered':
        post_dict[name] = True if select_filters else None
      else:
        logger.warning('Unexpected field type: ' + str(field))

  post_dict['format'] = fmt
  return post_dict


class AppReports(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.grants_report')
  template_success = 'grants/report_results.html'
  template_error = 'grants/reporting.html'

  def setUp(self): # don't super, can't set cycle dates with this fixture
    self.login_as_admin()

  def test_app_fields(self):
    """ Fetch all fields with no filters for browsing without error """

    form = AppReportForm()
    post_dict = fill_report_form(form, select_fields=True)
    post_dict['run-application'] = '' # simulate dropdown at top of page

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), models.GrantApplication.objects.count())

  def test_app_fields_csv(self):
    """ Fetched all fields without filters in csv format without error """

    form = AppReportForm()
    post_dict = fill_report_form(form, select_fields=True, fmt='csv')
    post_dict['run-application'] = '' # simulate dropdown at top of page

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding='utf8')
    row_count = sum(1 for row in reader)
    # 1st row is blank, 2nd is headers
    self.assertEqual(row_count - 2, models.GrantApplication.objects.count())

  @skip("Needs additional fixtures")
  def test_app_filters_all(self):
    """ Select/fill out all filters and verify that there are no errors """

    form = AppReportForm()
    post_dict = fill_report_form(form, select_fields=True, select_filters=True)
    post_dict['run-application'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(results, [])


class OrgReports(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.grants_report')
  template_success = 'grants/report_results.html'
  template_error = 'grants/reporting.html'

  def setUp(self): # don't super, can't set cycle dates with this fixture
    self.login_as_admin()

  def test_org_fields(self):
    """ Verify that org fields can be fetched

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of organizations in db
    """

    form = OrgReportForm()
    post_dict = fill_report_form(form, select_fields=True)
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), models.Organization.objects.count())

  def test_org_fields_csv(self):
    """ Verify that org fields can be fetched in csv format

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of orgs in db

    """

    form = OrgReportForm()
    post_dict = fill_report_form(form, select_fields=True, fmt='csv')
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding='utf8')
    row_count = sum(1 for row in reader)
    self.assertEqual(row_count - 2, models.Organization.objects.count())

  def test_org_filters_all(self):
    """ Verify that all filters can be selected in org report without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
    """

    form = OrgReportForm()
    post_dict = fill_report_form(form, select_fields=True, select_filters=True)
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(0, len(results))


class GPGReports(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.grants_report')
  template_success = 'grants/report_results.html'
  template_error = 'grants/reporting.html'

  def setUp(self): # don't super, can't set cycle dates with this fixture
    self.login_as_admin()

  def test_gp_grant_fields(self):
    """ Verify that gp grant fields can be fetched

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of gp grants in db
    """

    form = GPGrantReportForm()
    post_dict = fill_report_form(form, select_fields=True)
    post_dict['run-giving-project-grant'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), models.GivingProjectGrant.objects.count())

  def test_gp_grant_fields_csv(self):
    """ Verify that gp grant fields can be fetched in csv format

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of awards (gp + sponsored) in db

    """

    form = GPGrantReportForm()
    post_dict = fill_report_form(form, select_fields=True, fmt='csv')
    post_dict['run-giving-project-grant'] = ''

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding='utf8')
    row_count = sum(1 for row in reader)
    self.assertEqual(row_count - 2, models.GivingProjectGrant.objects.count())

  @skip("Needs additional fixtures")
  def test_gp_grant_filters_all(self):
    """ Verify that all filters can be selected in gp grant report without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
    """

    form = GPGrantReportForm()
    post_dict = fill_report_form(form, select_fields=True, select_filters=True)
    post_dict['run-giving-project-grant'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    logger.info(results)


class SponsoredAwardReports(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.grants_report')
  template_success = 'grants/report_results.html'
  template_error = 'grants/reporting.html'

  def setUp(self): # don't super, can't set cycle dates with this fixture
    self.login_as_admin()

  def test_sponsored_fields(self):
    """ Verify that sponsored grant fields can be fetched

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of gp grants in db
    """

    form = SponsoredAwardReportForm()
    post_dict = fill_report_form(form, select_fields=True)
    post_dict['run-sponsored-award'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), models.SponsoredProgramGrant.objects.count())

  def test_sponsored_grants_csv(self):
    """ Verify that sponsored grant fields can be fetched in csv format

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of awards (gp + sponsored) in db

    """

    form = SponsoredAwardReportForm()
    post_dict = fill_report_form(form, select_fields=True, fmt='csv')
    post_dict['run-sponsored-award'] = ''

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding='utf8')
    row_count = sum(1 for row in reader)
    self.assertEqual(row_count - 2, models.SponsoredProgramGrant.objects.count())

  def test_sponsored_all_filters(self):
    """ Verify that all filters can be selected without error """

    form = SponsoredAwardReportForm()
    post_dict = fill_report_form(form, select_fields=True, select_filters=True)
    post_dict['run-sponsored-award'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    logger.info(results)
