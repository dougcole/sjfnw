import json
import logging
from datetime import timedelta
from unittest import skip

from django.db.utils import IntegrityError
from django.forms.models import model_to_dict
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from sjfnw.grants import constants as gc, models
from sjfnw.grants.modelforms import get_form_for_cycle
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.tests.test_apply import BaseGrantFilesTestCase

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
      logger.error(form.errors)
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

@skip('TODO update')
class GranteeReport(BaseGrantTestCase):

  projectapp_id = 1

  def test_reports_due_two_year(self):
    first_report_due = timezone.now().date() + timedelta(days=9)

    award = models.GivingProjectGrant(
      projectapp_id=self.projectapp_id,
      amount=5000,
      second_amount=400,
      first_report_due=first_report_due
    )
    award.save()

    reportsdue = award.reports_due()

    self.assertEqual(award.grant_length(), 2)
    self.assert_length(reportsdue, 2)
    self.assertEqual(reportsdue[0], first_report_due)
    self.assertEqual(reportsdue[1], first_report_due.replace(year=first_report_due.year + 1))

  def test_reports_due_one(self):
    first_report_due = timezone.now().date() + timedelta(days=9)

    award = models.GivingProjectGrant(
      projectapp_id=self.projectapp_id,
      amount=5000,
      second_amount=0,
      first_report_due=first_report_due
    )
    award.save()

    reportsdue = award.reports_due()

    self.assertEqual(award.grant_length(), 1)
    self.assert_length(reportsdue, 1)
    self.assertEqual(reportsdue[0], first_report_due)

  def test_reports_due_completed(self):
    first_report_due = timezone.now().date() + timedelta(days=9)

    award = models.GivingProjectGrant(
      projectapp_id=self.projectapp_id,
      amount=5000,
      second_amount=0,
      first_report_due=first_report_due
    )
    award.save()
    report = models.GranteeReport(
      giving_project_grant=award, total_size=83, donations_count_prev=6, donations_count=9,
      other_comments='Critical feedback'
    )
    report.save()
    reportsdue = award.reports_due()

    self.assertEqual(award.grant_length(), 1)
    self.assert_length(reportsdue, 0)

class ReportQuestion(BaseGrantTestCase):

  def test_defaults(self):
    question = models.ReportQuestion(name='any name', version='v3', text='Answer this')
    self.assertEqual(question.input_type, gc.QuestionTypes.TEXT)
    self.assertEqual(question.word_limit, 750)
    self.assertIsNone(question.archived)
    self.assertEqual(question.display_name(), u'Any Name')
    self.assertEqual(unicode(question), u'Any Name (v3)')

class ReportAnswer(TestCase):

  def test_required_fields(self):
    try:
      answer = models.ReportAnswer()
      answer.save()
    except IntegrityError as err:
      self.assertEqual(err.message,
        'NOT NULL constraint failed: grants_reportanswer.cycle_report_question_id')
    else:
      logger.warn(model_to_dict(answer))
      raise Exception('Expected ReportAnswer to error without any args')

  def test_valid(self):
    award = factories.GivingProjectGrant()
    report = factories.GranteeReport(giving_project_grant=award)
    cycle_report_question = models.CycleReportQuestion.objects.filter(
      grant_cycle=award.projectapp.application.grant_cycle).first()
    answer = models.ReportAnswer(
      cycle_report_question=cycle_report_question,
      grantee_report=report,
      text='Here is my answer'
    )
    self.assertEqual(answer.get_question_text(), cycle_report_question.report_question.text)
