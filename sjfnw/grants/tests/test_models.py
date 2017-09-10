import json
import logging
from datetime import timedelta
from unittest import skip

from django.forms.models import model_to_dict
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from sjfnw.grants import constants as gc
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.tests.test_apply import BaseGrantFilesTestCase
from sjfnw.grants import models
from sjfnw.grants.modelforms import get_form_for_cycle

logger = logging.getLogger('sjfnw')

@override_settings(MEDIA_ROOT='sjfnw/grants/tests/media/',
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    FILE_UPLOAD_HANDLERS=('django.core.files.uploadhandler.MemoryFileUploadHandler',))
class DraftManager(BaseGrantFilesTestCase):

  def test_refs(self):
    app = factories.GrantApplication()

    collab_refs = json.loads(app.get_narrative_answer('collaboration_references'))
    rj_refs = json.loads(app.get_narrative_answer('racial_justice_references'))

    draft = models.DraftGrantApplication.objects.create_from_submitted_app(app)
    contents = json.loads(draft.contents)

    self.assertNotIn('racial_justice_references', contents)
    self.assertNotIn('collaboration_references', contents)
    self.assertEqual(contents['racial_justice_references_0'], rj_refs[0]['name'])
    self.assertEqual(contents['racial_justice_references_1'], rj_refs[0]['org'])
    self.assertEqual(contents['racial_justice_references_2'], rj_refs[0]['phone'])
    self.assertEqual(contents['racial_justice_references_3'], rj_refs[0]['email'])
    self.assertEqual(contents['racial_justice_references_4'], rj_refs[1]['name'])
    self.assertEqual(contents['racial_justice_references_5'], rj_refs[1]['org'])
    self.assertEqual(contents['racial_justice_references_6'], rj_refs[1]['phone'])
    self.assertEqual(contents['racial_justice_references_7'], rj_refs[1]['email'])
    self.assertEqual(contents['collaboration_references_0'], collab_refs[0]['name'])
    self.assertEqual(contents['collaboration_references_1'], collab_refs[0]['org'])
    self.assertEqual(contents['collaboration_references_2'], collab_refs[0]['phone'])
    self.assertEqual(contents['collaboration_references_3'], collab_refs[0]['email'])
    self.assertEqual(contents['collaboration_references_4'], collab_refs[1]['name'])
    self.assertEqual(contents['collaboration_references_5'], collab_refs[1]['org'])
    self.assertEqual(contents['collaboration_references_6'], collab_refs[1]['phone'])
    self.assertEqual(contents['collaboration_references_7'], collab_refs[1]['email'])

    # get fields & files from draft
    draft_data = json.loads(draft.contents)
    files_data = model_to_dict(draft, fields=draft.file_fields())

    # add automated fields
    draft_data['organization'] = draft.organization.pk
    draft_data['grant_cycle'] = draft.grant_cycle.pk

    app.delete()

    form = get_form_for_cycle(draft.grant_cycle)(draft.grant_cycle, draft_data, files_data)
    if not form.is_valid():
      raise Exception('Expected form to be valid')


class GrantApplication(BaseGrantTestCase):

  def test_get_narrative_answer(self):
    app = factories.GrantApplication()

    answers = models.NarrativeAnswer.objects.filter(grant_application=app)

    self.assert_count(answers, len(gc.STANDARD_NARRATIVES))
    self.assertNotEqual(app.get_narrative_answer('describe_mission'),
        answers.get(cycle_narrative__narrative_question__name='describe_mission'))

  @skip('TODO')
  def test_updates_profile(self):
    pass

  @skip('TODO')
  def test_doesnt_update_profile(self):
    pass

class OrganizationGetStaffEntered(TestCase):

  def test_none(self):
    org = models.Organization()
    self.assertEqual(org.get_staff_entered_contact_info(), '')

  def test_some(self):
    org = models.Organization(staff_contact_person_title='Mx', staff_contact_email='who@what.z')
    self.assertEqual(org.get_staff_entered_contact_info(), 'Mx, who@what.z')

  def test_all(self):
    org = models.Organization(
      staff_contact_person='Ray',
      staff_contact_person_title='Mx',
      staff_contact_phone='555-999-4242',
      staff_contact_email='who@what.z'
    )
    self.assertEqual(org.get_staff_entered_contact_info(), 'Ray, Mx, 555-999-4242, who@what.z')

class YearEndReportModel(BaseGrantTestCase):

  projectapp_id = 1

  def test_yers_due_two_year(self):
    first_yer_due = timezone.now().date() + timedelta(days=9)

    award = models.GivingProjectGrant(
      projectapp_id=self.projectapp_id,
      amount=5000,
      second_amount=400,
      first_yer_due=first_yer_due
    )
    award.save()

    yersdue = award.yers_due()

    self.assertEqual(award.grant_length(), 2)
    self.assert_length(yersdue, 2)
    self.assertEqual(yersdue[0], first_yer_due)
    self.assertEqual(yersdue[1], first_yer_due.replace(year=first_yer_due.year + 1))

  def test_yers_due_one(self):
    first_yer_due = timezone.now().date() + timedelta(days=9)

    award = models.GivingProjectGrant(
      projectapp_id=self.projectapp_id,
      amount=5000,
      second_amount=0,
      first_yer_due=first_yer_due
    )
    award.save()

    yersdue = award.yers_due()

    self.assertEqual(award.grant_length(), 1)
    self.assert_length(yersdue, 1)
    self.assertEqual(yersdue[0], first_yer_due)

  def test_yers_due_completed(self):
    first_yer_due = timezone.now().date() + timedelta(days=9)

    award = models.GivingProjectGrant(
      projectapp_id=self.projectapp_id,
      amount=5000,
      second_amount=0,
      first_yer_due=first_yer_due
    )
    award.save()
    yer = models.YearEndReport(
      award=award, total_size=83, donations_count_prev=6, donations_count=9,
      other_comments='Critical feedback'
    )
    yer.save()
    yersdue = award.yers_due()

    self.assertEqual(award.grant_length(), 1)
    self.assert_length(yersdue, 0)
