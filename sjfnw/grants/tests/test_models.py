from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from sjfnw.grants import constants as gc
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.models import (Organization, GrantApplication,
    GivingProjectGrant, NarrativeAnswer, YearEndReport)

class GrantApplication(BaseGrantTestCase):

  def test_get_narrative_answer(self):
    app = factories.GrantApplication()

    answers = NarrativeAnswer.objects.filter(grant_application=app)

    self.assert_count(answers, len(gc.STANDARD_NARRATIVES))
    self.assertNotEqual(app.get_narrative_answer('describe_mission'), answers.get(cycle_narrative__narrative_question__name='describe_mission'))

class OrganizationGetStaffEntered(TestCase):

  def test_none(self):
    org = Organization()
    self.assertEqual(org.get_staff_entered_contact_info(), '')

  def test_some(self):
    org = Organization(staff_contact_person_title='Mx', staff_contact_email='who@what.z')
    self.assertEqual(org.get_staff_entered_contact_info(), 'Mx, who@what.z')

  def test_all(self):
    org = Organization(
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

    award = GivingProjectGrant(
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

    award = GivingProjectGrant(
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

    award = GivingProjectGrant(
      projectapp_id=self.projectapp_id,
      amount=5000,
      second_amount=0,
      first_yer_due=first_yer_due
    )
    award.save()
    yer = YearEndReport(
      award=award, total_size=83, donations_count_prev=6, donations_count=9,
      other_comments='Critical feedback'
    )
    yer.save()
    yersdue = award.yers_due()

    self.assertEqual(award.grant_length(), 1)
    self.assert_length(yersdue, 0)
