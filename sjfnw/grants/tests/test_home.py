from datetime import timedelta
import json, logging

from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.models import (DraftGrantApplication, GrantApplication,
    GivingProjectGrant)

logger = logging.getLogger('sjfnw')

class OrgHomeAwards(BaseGrantTestCase):
  """ Verify that correct data is showing on the org home page """

  url = reverse('grants:home')
  template = 'grants/org_home.html'

  def setUp(self):
    super(OrgHomeAwards, self).setUp()
    self.login_as_org()

  def test_none(self):
    self.assert_count(
      GivingProjectGrant.objects.filter(projectapp__application__organization=self.org),
      0)

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertNotContains(response, 'Agreement mailed')

  def test_early(self):
    """ org has an award, but agreement has not been mailed. verify not shown """
    factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      agreement_mailed=None
    )

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertNotContains(response, 'Agreement mailed')

  def test_sent(self):
    today = timezone.now()
    factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      agreement_mailed=today - timedelta(days=1),
      first_yer_due=today + timedelta(weeks=52)
    )

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertContains(response, 'Agreement mailed')

class OrgRollover(BaseGrantTestCase):

  def setUp(self):
    super(OrgRollover, self).setUp()
    self.login_as_org()

  def test_draft_rollover(self):
    draft = factories.DraftGrantApplication(organization=self.org)
    target_cycle = factories.GrantCycle(status='open')

    response = self.client.post('/apply/copy',
        {'cycle': target_cycle.pk, 'draft': draft.pk, 'application': ''}, follow=True)

    ids = {'organization_id': self.org.pk, 'grant_cycle_id': target_cycle.pk}
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')

    new_draft = DraftGrantApplication.objects.get(**ids)
    old_contents = json.loads(draft.contents)
    new_contents = json.loads(new_draft.contents)
    self.assertEqual(old_contents, new_contents)
    for field in GrantApplication.file_fields():
      if hasattr(draft, field):
        self.assertEqual(getattr(draft, field), getattr(new_draft, field))

  def test_app_rollover(self):
    app = factories.GrantApplication(organization=self.org)
    target_cycle = factories.GrantCycle(status='open')

    post_data = {'cycle': target_cycle.pk, 'draft': '', 'application': app.pk}
    response = self.client.post('/apply/copy', post_data, follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')

    ids = {'organization_id': self.org.pk, 'grant_cycle_id': target_cycle.pk}

    draft = DraftGrantApplication.objects.get(**ids)
    self.assert_draft_matches_app(draft, app)
