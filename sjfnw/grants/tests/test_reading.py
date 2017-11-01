import logging
from unittest import skip

from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.grants import constants as gc, views
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.models import GivingProjectGrant, ProjectApp, GranteeReport

logger = logging.getLogger('sjfnw')


class GrantReading(BaseGrantTestCase):

  def setUp(self):
    super(GrantReading, self).setUp()
    award = factories.GivingProjectGrant(first_report_due=timezone.now())
    report = factories.GranteeReport(giving_project_grant=award)
    self.report_id = report.pk

  def _get_url(self, app_id):
    return reverse(views.view_application, kwargs={'app_id': app_id})

  def test_author(self):
    self.login_as_org()
    app = factories.GrantApplication(organization=self.org)
    report = factories.GranteeReport(giving_project_grant__projectapp__application=app)

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(3, res.context['perm'])
    self.assertContains(res, 'grantee report')

  def test_other_org(self):
    self.login_as_org()
    app = factories.GrantApplication()
    report = factories.GranteeReport(giving_project_grant__projectapp__application=app)

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(0, res.context['perm'])
    self.assertNotContains(res, 'grantee report')

  def test_staff(self):
    self.login_as_admin()
    app = factories.GrantApplication()

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(2, res.context['perm'])

  @skip('TODO fund factories')
  def test_valid_member_not_visible(self):
    self.login_as_member('first')

    res = self.client.get(self._get_url(1), follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(1, res.context['perm'])
    self.assertNotContains(res, 'grantee report')

  @skip('TODO fund factories')
  def test_invalid_member_not_visible(self):
    self.login_as_member('blank')

    res = self.client.get(self._get_url(1), follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(0, res.context['perm'])
    self.assertNotContains(res, 'grantee report')

  @skip('TODO fund factories')
  def test_valid_member_visible(self):
    self.login_as_member('first')
    report = GranteeReport.objects.get(pk=self.report_id)
    report.visible = True
    report.save()

    res = self.client.get(self.reading_url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(1, res.context['perm'])

  @skip('TODO set up report')
  def test_invalid_member_visible(self):
    self.login_as_member('blank')
    report = GranteeReport.objects.get(pk=self.report_id)
    report.visible = True
    report.save()

    res = self.client.get(self.reading_url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(0, res.context['perm'])
    self.assertNotContains(res, 'grantee report')

  def test_two_year_grant_question(self):
    self.login_as_org()

    app = factories.GrantApplication(
      organization=self.org,
      grant_cycle__narrative_questions__add=[gc.TWO_YEAR_GRANT_QUESTION])

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(3, res.context['perm'])
    self.assertContains(res, app.get_narrative_answer('two_year_grant'))
