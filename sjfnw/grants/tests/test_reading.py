import logging
from unittest import skip

from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.grants import constants as gc, views
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.models import (GivingProjectGrant, GrantCycle, ProjectApp,
    YearEndReport)

logger = logging.getLogger('sjfnw')


class GrantReading(BaseGrantTestCase):

  def setUp(self):
    super(GrantReading, self).setUp()
    award = factories.GivingProjectGrant(first_yer_due=timezone.now())
    yer = factories.YearEndReport(award=award)
    self.yer_id = yer.pk

  def _get_url(self, app_id):
    return reverse(views.view_application, kwargs={'app_id': app_id})

  def test_author(self):
    self.login_as_org()
    app = factories.GrantApplication(organization=self.org)

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(3, res.context['perm'])
    self.assertContains(res, 'year end report')

  def test_other_org(self):
    self.login_as_org()
    app = factories.GrantApplication()

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(0, res.context['perm'])
    self.assertNotContains(res, 'year end report')

  def test_staff(self):
    self.login_as_admin()
    app = factories.GrantApplication()

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(2, res.context['perm'])
    self.assertContains(res, 'year end report')

  @skip('TODO fund factories')
  def test_valid_member_not_visible(self):
    self.login_as_member('first')

    res = self.client.get(self.reading_url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(1, res.context['perm'])
    self.assertNotContains(res, 'year end report')

  def test_invalid_member_not_visible(self):
    self.login_as_member('blank')

    res = self.client.get(self.reading_url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(0, res.context['perm'])
    self.assertNotContains(res, 'year end report')

  @skip('TODO fund factories')
  def test_valid_member_visible(self):
    self.login_as_member('first')
    yer = YearEndReport.objects.get(pk=self.yer_id)
    yer.visible = True
    yer.save()

    res = self.client.get(self.reading_url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(1, res.context['perm'])

  @skip('TODO set up YER')
  def test_invalid_member_visible(self):
    self.login_as_member('blank')
    yer = YearEndReport.objects.get(pk=self.yer_id)
    yer.visible = True
    yer.save()

    res = self.client.get(self.reading_url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(0, res.context['perm'])
    self.assertNotContains(res, 'year end report')

  def test_two_year_grant_question(self):
    self.login_as_org()

    app = factories.GrantApplication(
      organization=self.org,
      grant_cycle__questions__add=[gc.TWO_YEAR_GRANT_QUESTION])

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/reading.html')
    self.assertEqual(3, res.context['perm'])
    self.assertContains(res, app.get_narrative_answer('two_year_grant'))
