from datetime import timedelta
import json, logging

from django.core import mail
from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.grants import cron, models, views
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase


class DraftAutosave(BaseGrantTestCase):

  def _get_url(self, draft):
    return reverse('grants:autosave_app', kwargs={'cycle_id': draft.grant_cycle.pk})

  def setUp(self):
    super(DraftAutosave, self).setUp()

  def test_valid(self):
    self.login_as_org()
    draft = factories.DraftGrantApplication(organization=self.org)

    response = self.client.post(self._get_url(draft), {})

    self.assertEqual(200, response.status_code)
    draft.refresh_from_db()
    self.assertEqual(draft.contents, '{}')

  def test_not_logged_in(self):
    draft = factories.DraftGrantApplication()
    response = self.client.post(self._get_url(draft), {'mission': 'Something'})
    self.assertEqual(401, response.status_code)


class DraftWarning(BaseGrantTestCase):

  def setUp(self):
    super(DraftWarning, self).setUp()
    self.login_as_admin()

  def test_long_alert(self):
    now = timezone.now()
    cycle = factories.GrantCycle(close=now + timedelta(days=7, hours=12))
    draft = factories.DraftGrantApplication(
      grant_cycle=cycle,
      created=now - timedelta(days=12)
    )

    self.assert_length(mail.outbox, 0)
    self.client.get(reverse(cron.draft_app_warning))
    self.assert_length(mail.outbox, 1)

  def test_long_alert_skip(self):
    now = timezone.now()
    cycle = factories.GrantCycle(close=now + timedelta(days=7, hours=12))
    draft = factories.DraftGrantApplication(grant_cycle=cycle, created=now)

    self.assert_length(mail.outbox, 0)
    self.client.get(reverse(cron.draft_app_warning))
    self.assert_length(mail.outbox, 0)

  def test_short_alert(self):
    """ Cycle created now with cycle closing in 2.5 days """

    now = timezone.now()
    cycle = factories.GrantCycle(close=now + timedelta(days=2, hours=12))
    draft = factories.DraftGrantApplication(grant_cycle=cycle, created=now)

    self.assert_length(mail.outbox, 0)
    self.client.get(reverse(cron.draft_app_warning))
    self.assert_length(mail.outbox, 1)

  def test_short_alert_ignore(self):
    now = timezone.now()
    cycle = factories.GrantCycle(close=now + timedelta(days=2, hours=12))
    draft = factories.DraftGrantApplication(
      grant_cycle=cycle,
      created=now - timedelta(days=12)
    )

    self.assert_length(mail.outbox, 0)
    self.client.get(reverse(cron.draft_app_warning))
    self.assert_length(mail.outbox, 0)


class DiscardDraft(BaseGrantTestCase):

  url = reverse('grants:discard_draft', kwargs={'draft_id': 1})

  def setUp(self):
    super(DiscardDraft, self).setUp()
    self.login_as_org()

  def test_post(self):
    """ Wrong http method - should have no effect """
    draft = factories.DraftGrantApplication(organization=self.org)

    response = self.client.post(self.url)

    self.assertEqual(response.status_code, 405)
    self.assertEqual(response.get('Allow'), 'DELETE')
    self.assert_count(models.DraftGrantApplication.objects.filter(pk=draft.pk), 1)

  def test_valid_delete(self):
    draft = factories.DraftGrantApplication(organization=self.org)

    response = self.client.delete(self.url)

    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.content, 'success')
    self.assert_count(
      models.DraftGrantApplication.objects.filter(organization=self.org),
      0)

  def test_draft_not_found(self):
    self.assert_count(models.DraftGrantApplication.objects.filter(pk=84), 0)

    response = self.client.delete(
      reverse('grants:discard_draft', kwargs={'draft_id': 84})
    )
    self.assertEqual(response.status_code, 404)
    self.assertEqual(response.content, '')

  def test_wrong_org(self):
    other_org = factories.Organization()
    draft = factories.DraftGrantApplication(organization=other_org)

    response = self.client.delete(self.url)
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.content, 'User does not have permission to delete this draft')


class DraftRemoveFile(BaseGrantTestCase):

  def setUp(self):
    self.login_as_org()
    self.draft = factories.DraftGrantApplication()

  def test_unknown_draft_type(self):

    url = reverse('grants:remove_file', kwargs={
      'draft_type': 'madeup', 'draft_id': self.draft.pk, 'file_field': 'budget1'
    })
    res = self.client.get(url)
    self.assertEqual(res.status_code, 400)

  def test_obj_not_found(self):

    url = reverse('grants:remove_file', kwargs={
      'draft_type': 'apply', 'draft_id': '1880', 'file_field': 'budget1'
    })
    res = self.client.get(url, follow=True)
    self.assertEqual(res.status_code, 404)

  def test_unknown_field(self):

    url = reverse('grants:remove_file', kwargs={
      'draft_type': 'apply', 'draft_id': self.draft.pk, 'file_field': 'madeup'
    })

    modified = self.draft.modified

    res = self.client.get(url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.draft.refresh_from_db()
    modified_after = self.draft.modified
    self.assertEqual(modified, modified_after)

  def test_remove_draft_app_file(self):
    self.assertTrue(len(self.draft.budget1.name) > 1)

    url = reverse('grants:remove_file', kwargs={
      'draft_type': 'apply', 'draft_id': self.draft.pk, 'file_field': 'budget1'
    })

    res = self.client.get(url, follow=True)

    self.assertEqual(res.status_code, 200)

    self.draft.refresh_from_db()
    self.assertFalse(self.draft.budget1)
    self.assertEqual(self.draft.budget1.name, '')

  def test_remove_draft_yer_file(self):
    draft = factories.YERDraft(award__projectapp__application__organization=self.org)
    self.assertTrue(draft.photo_release)

    url = reverse('grants:remove_file', kwargs={
      'draft_type': 'report', 'draft_id': draft.pk, 'file_field': 'photo_release'
    })
    res = self.client.get(url, follow=True)

    self.assertEqual(res.status_code, 200)

    draft.refresh_from_db()
    self.assertFalse(draft.photo_release)
    self.assertEqual(draft.photo_release.name, '')
