from datetime import timedelta
import json
import logging
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from google.appengine.ext import testbed
from google.appengine.api import blobstore, datastore

from sjfnw.grants import constants as gc, views
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.models import (Organization, DraftGrantApplication,
  GrantApplication, GrantCycle, NarrativeAnswer)

logger = logging.getLogger('sjfnw')

def _get_apply_url(cycle_id):
  return reverse(views.grant_application, kwargs={'cycle_id': cycle_id})

class BaseGrantFilesTestCase(BaseGrantTestCase):
  """ Subclass of BaseGrantTestCase that can handle file uploads """

  def setUp(self):
    super(BaseGrantFilesTestCase, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_blobstore_stub()

  def tearDown(self):
    self.testbed.deactivate()

  def create_blob(self, key, **kwargs):
    blobstore_stub = self.testbed.get_stub('blobstore')
    entity = datastore.Entity(blobstore.BLOB_INFO_KIND, name=key, namespace='')
    entity['size'] = len(kwargs['content'])
    entity['filename'] = kwargs['filename']
    entity['content_type'] = kwargs['content_type']
    datastore.Put(entity)
    blobstore_stub.storage.CreateBlob('fakeblobkey123', kwargs['content'])


def alter_draft_contents(draft, updates):
  contents_dict = json.loads(draft.contents)
  contents_dict.update(updates)
  draft.contents = json.dumps(contents_dict)
  draft.save()

def alter_draft_timeline(draft, values):
  """ Helper method to set timeline field on draft
    Args:
      values: list of timeline widget values (0-14)
  """
  contents_dict = json.loads(draft.contents)
  for i in range(15):
    contents_dict['timeline_' + str(i)] = values[i]
  draft.contents = json.dumps(contents_dict)
  draft.save()


def alter_draft_files(draft, file_values):
  """ Helper method to update draft's file fields
  Args:
    file_values: list, should match this order:
      ['demographics', 'funding_sources', 'budget1', 'budget2',
       'budget3', 'project_budget_file', 'fiscal_letter']
  """
  files = dict(zip(DraftGrantApplication.file_fields(), file_values))
  for key, val in files.iteritems():
    setattr(draft, key, val)
  draft.save()


class CycleInfo(BaseGrantTestCase):

  error_message = 'Grant cycle information page could not be loaded'

  def _get_url(self, cycle_id):
    return reverse(views.cycle_info, kwargs={'cycle_id': cycle_id})

  def test_no_url(self):
    cycle = factories.GrantCycle(status='open', info_page='')

    res = self.client.get(self._get_url(cycle.pk), follow=True)
    self.assertEqual(res.status_code, 404)

  def test_not_allowed_url(self):
    cycle = factories.GrantCycle(status='open', info_page='http://facebook.com')

    res = self.client.get(self._get_url(cycle.pk), follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/cycle_info.html')
    self.assertContains(res, self.error_message)
    self.assertContains(res, 'You can still continue')
    self.assertNotContains(res, 'facebook')

  def test_invalid_url(self):
    info_page = 'http://socialjusticefund.org/does-not-exist'
    cycle = factories.GrantCycle(status='open', info_page=info_page)

    res = self.client.get(self._get_url(cycle.pk), follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/cycle_info.html')
    self.assertContains(res, self.error_message)
    self.assertContains(res, 'Try visiting it directly')
    self.assertContains(res, 'a href="{}"'.format(info_page))

  def test_valid_url(self):
    cycle = factories.GrantCycle(
      status='open',
      info_page='http://www.socialjusticefund.org/grant-app/criminal-justice-grant-cycle-2014'
    )

    res = self.client.get(self._get_url(cycle.pk), follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/cycle_info.html')
    self.assertNotContains(res, self.error_message)
    self.assertContains(res, 'node-grant-portal-info-page')


@override_settings(MEDIA_ROOT='sjfnw/grants/tests/media/',
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    FILE_UPLOAD_HANDLERS=('django.core.files.uploadhandler.MemoryFileUploadHandler',))
class ApplySuccessful(BaseGrantFilesTestCase):

  cycle_id = 2

  def setUp(self):
    super(ApplySuccessful, self).setUp()
    self.login_as_org()

  def test_saved_timeline1(self):
    """ Verify that a timeline with just a complete first row is accepted """

    answers = ['Jan', 'Chillin', 'Not applicable',
               '', '', '', '', '', '', '', '', '', '', '', '']

    draft = factories.DraftGrantApplication(organization=self.org)
    alter_draft_timeline(draft, answers)

    res = self.client.post(_get_apply_url(draft.grant_cycle.pk), follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/submitted.html')
    app = GrantApplication.objects.get(organization=self.org)
    self.assertEqual(app.get_narrative_answer('timeline'), json.dumps(answers))

  def test_saved_timeline5(self):
    """ Verify that a completely filled out timeline is accepted """

    answers = [
      'Jan', 'Chillin', 'Not applicable',
      'Feb', 'Petting dogs', '5 dogs',
      'Mar', 'Planting daffodils', 'Sprouts',
      'July', 'Walking around Greenlake', '9 times',
      'August', 'Reading in the shade', 'No sunburns'
    ]

    draft = factories.DraftGrantApplication(organization=self.org)
    alter_draft_timeline(draft, answers)

    res = self.client.post(_get_apply_url(draft.grant_cycle.pk), follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/submitted.html')
    app = GrantApplication.objects.get(organization=self.org)
    self.assertEqual(app.get_narrative_answer('timeline'), json.dumps(answers))

  def test_mult_budget(self):
    """ scenario: budget1, budget2, budget3

        verify: successful submission & files match  """

    draft = factories.DraftGrantApplication(organization=self.org)
    files = ['funding_sources.docx', 'diversity.doc', 'budget1.docx',
             'budget2.txt', 'budget3.png', '', '']
    alter_draft_files(draft, files)

    res = self.client.post(_get_apply_url(draft.grant_cycle.pk), follow=True)

    self.assertTemplateUsed(res, 'grants/submitted.html')
    self.assert_count(DraftGrantApplication.objects.filter(organization=self.org), 0)
    app = GrantApplication.objects.get(organization=self.org, grant_cycle=draft.grant_cycle)
    self.assertEqual(app.budget1, files[2])
    self.assertEqual(app.budget2, files[3])

  def test_profile_updated(self):
    """ Verify that org profile is updated when application is submitted
    Just checks mission field """

    draft = factories.DraftGrantApplication(organization=self.org)
    draft_contents = json.loads(draft.contents)

    self.assertNotEqual(draft_contents['mission'], self.org.mission)

    res = self.client.post(_get_apply_url(draft.grant_cycle.pk), follow=True)

    self.org.refresh_from_db()
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/submitted.html')
    self.assertEqual(draft_contents['mission'], self.org.mission)


class ApplyBlocked(BaseGrantTestCase):

  def setUp(self):
    super(ApplyBlocked, self).setUp()
    self.login_as_org()

  def test_closed_cycle(self):
    cycle = factories.GrantCycle(status='closed')
    res = self.client.get(_get_apply_url(cycle.pk))
    self.assertEqual(200, res.status_code)
    self.assertTemplateUsed(res, 'grants/closed.html')

  def test_upcoming(self):
    cycle = factories.GrantCycle(status='upcoming')
    res = self.client.get(_get_apply_url(cycle.pk))
    self.assertEqual(200, res.status_code)
    self.assertTemplateUsed(res, 'grants/closed.html')

  def test_nonexistent(self):
    res = self.client.get(_get_apply_url(0))
    self.assertEqual(404, res.status_code)

  def test_already_submitted(self):
    app = factories.GrantApplication(organization=self.org)
    ids = {'organization': self.org, 'grant_cycle_id': app.grant_cycle.pk}

    res = self.client.get(_get_apply_url(app.grant_cycle.pk))

    self.assertEqual(200, res.status_code)
    self.assertTemplateUsed(res, 'grants/already_applied.html')
    self.assert_count(DraftGrantApplication.objects.filter(organization=self.org), 0)


class ApplyValidation(BaseGrantFilesTestCase):

  def setUp(self):
    super(ApplyValidation, self).setUp()
    self.login_as_org()
    # take a valid grant application to use as draft
    app = factories.GrantApplication()
    self.draft = DraftGrantApplication.objects.create_from_submitted_app(app, save=False)
    self.draft.organization = self.org
    self.draft.grant_cycle = factories.GrantCycle(status='open')

  def test_project_requirements(self):
    alter_draft_contents(self.draft, {'support_type': 'Project support'})

    res = self.client.post(_get_apply_url(self.draft.grant_cycle.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_app.html')
    filter_by = {'organization': self.org, 'grant_cycle': self.draft.grant_cycle}
    self.assert_count(GrantApplication.objects.filter(**filter_by), 0)
    self.assert_count(DraftGrantApplication.objects.filter(**filter_by), 1)

    self.assertFormError(res, 'form', 'project_title',
        'This field is required when applying for project support.')
    self.assertFormError(res, 'form', 'project_budget',
        'This field is required when applying for project support.')

  def test_timeline_incomplete(self):
    answers = ['Jan', 'Chillin', 'Not applicable',
               'Feb', 'Petting dogs', '5 dogs',
               'Mar', '', 'Sprouts',
               'July', '', '',
               '', 'Reading in the shade', 'No sunburns']
    alter_draft_timeline(self.draft, answers)

    res = self.client.post(_get_apply_url(self.draft.grant_cycle_id))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_app.html')
    self.assertFormError(res, 'form', 'timeline',
        'All three columns are required for each '
        'quarter that you include in your timeline.')

  def test_timeline_empty(self):
    answers = ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
    alter_draft_timeline(self.draft, answers)

    res = self.client.post(_get_apply_url(self.draft.grant_cycle_id))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_app.html')
    self.assertFormError(res, 'form', 'timeline', 'This field is required.')

  def test_narratives_missing(self):
    alter_draft_contents(self.draft, {
      'collaboration': ''
    })

    res = self.client.post(_get_apply_url(self.draft.grant_cycle_id))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_app.html')
    self.assertFormError(res, 'form', 'collaboration', 'This field is required.')


class StartApplication(BaseGrantTestCase):

  def _load_application_form(self, cycle_id):
    """ Goes through initial cycle info load, returns application form response """

    query_kwargs={'grant_cycle_id': cycle_id, 'organization': self.org}
    view_kwargs = {'cycle_id': cycle_id}
    url = reverse(views.grant_application, kwargs=view_kwargs) + '?info=1'

    # start with no draft
    self.assert_count(DraftGrantApplication.objects.filter(**query_kwargs), 0)

    # should render grant application form and create draft
    res = self.client.get(url)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_app.html')
    self.assert_count(DraftGrantApplication.objects.filter(**query_kwargs), 1)
    return res

  def test_load_first_app(self):
    self.login_as_org()

    cycle = factories.GrantCycle(status='open')
    res = self._load_application_form(cycle.pk)

    self.assertNotContains(res, 'Pre-filled')

  def test_load_second_app(self):
    self.login_as_org(with_profile=True)

    cycle = factories.GrantCycle(status='open')

    res = self._load_application_form(cycle.pk)

    # mission should be pre-filled using last application
    org = Organization.objects.get(pk=self.org.pk)
    self.assertContains(res, 'Pre-filled')
    self.assertContains(res, org.mission)


class AddFile(BaseGrantFilesTestCase):

  def test_draft_not_found(self):
    url = reverse('sjfnw.grants.views.add_file',
                  kwargs={'draft_type': 'apply', 'draft_id': 0})
    res = self.client.get(url, follow=True)
    self.assertEqual(res.status_code, 404)

  def test_invalid_type(self):
    url = reverse('sjfnw.grants.views.add_file',
                  kwargs={'draft_type': 'what', 'draft_id': 2})
    res = self.client.get(url, follow=True)
    self.assertEqual(res.status_code, 404)

  def test_valid(self):
    draft = factories.DraftGrantApplication()
    original = draft.budget3

    self.create_blob('fakeblobkey123', filename='file.txt',
                     content_type='text', content='filler')

    url = reverse(views.add_file,
                  kwargs={'draft_type': 'apply', 'draft_id': draft.pk})
    budget = SimpleUploadedFile("file.txt", "blob-key=fakeblobkey123")
    res = self.client.post(url, {'budget3': budget}, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertContains(res, 'file.txt')
    draft.refresh_from_db()
    self.assertEqual(draft.budget3.name, 'fakeblobkey123/file.txt')
    self.assertNotEqual(draft.budget3, original)
