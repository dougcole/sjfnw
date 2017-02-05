import logging

from django.utils import timezone

from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.models import (GivingProjectGrant, GrantApplicationOverflow,
    GrantCycle, ProjectApp, YearEndReport)

logger = logging.getLogger('sjfnw')


class GrantReading(BaseGrantTestCase):

  fixtures = ['sjfnw/grants/fixtures/test_grants.json',
              'sjfnw/fund/fixtures/test_fund.json']

  def setUp(self):
    super(GrantReading, self).setUp()
    papp = ProjectApp(application_id=1, giving_project_id=1)
    papp.save()
    award = GivingProjectGrant(projectapp_id=papp.pk, amount=8900, first_yer_due=timezone.now())
    award.save()
    yer = YearEndReport(
      award=award, total_size=83, donations_count_prev=6, donations_count=9,
      other_comments='Critical feedback'
    )
    yer.save()
    self.yer_id = yer.pk

  def test_author(self):
    self.login_as_org('test')

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(3, response.context['perm'])
    self.assertContains(response, 'year end report')

  def test_other_org(self):
    self.login_as_org('new')

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(0, response.context['perm'])
    self.assertNotContains(response, 'year end report')

  def test_staff(self):
    self.login_as_admin()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(2, response.context['perm'])
    self.assertContains(response, 'year end report')

  def test_valid_member_not_visible(self):
    self.login_as_member('first')

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(1, response.context['perm'])
    self.assertNotContains(response, 'year end report')

  def test_invalid_member_not_visible(self):
    self.login_as_member('blank')

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(0, response.context['perm'])
    self.assertNotContains(response, 'year end report')

  def test_valid_member_visible(self):
    self.login_as_member('first')
    yer = YearEndReport.objects.get(pk=self.yer_id)
    yer.visible = True
    yer.save()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(1, response.context['perm'])
    self.assertContains(response, 'year end report')

  def test_invalid_member_visible(self):
    self.login_as_member('blank')
    yer = YearEndReport.objects.get(pk=self.yer_id)
    yer.visible = True
    yer.save()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(0, response.context['perm'])
    self.assertNotContains(response, 'year end report')

  def test_two_year_grant_question(self):
    self.login_as_org('test')

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(3, response.context['perm'])
    self.assertContains(response, 'year end report')
    self.assertNotContains(response, 'two-year grants')

    # View the app again after adding text to its two_year_question field
    cycle = GrantCycle.objects.get(pk=1)
    cycle.two_year_grants = True
    cycle.save()
    overflow = GrantApplicationOverflow(grant_application_id=1,
        two_year_question='A response about two-year grants')
    overflow.save()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(3, response.context['perm'])
    self.assertContains(response, 'year end report')
    self.assertContains(response, cycle.two_year_question)
    self.assertContains(response, 'two-year grants')
