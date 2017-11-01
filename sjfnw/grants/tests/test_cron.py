import logging
from datetime import timedelta
from mock import Mock

from django.core import mail
from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.tests.base import BaseTestCase
from sjfnw.grants import constants as gc, models
from sjfnw.grants.cron import auto_create_cycles
from sjfnw.grants.tests import factories

logger = logging.getLogger('sjfnw')

class AutoCreateCycles(BaseTestCase):

  url = reverse(auto_create_cycles)

  def test_wrong_time(self):
    timezone.now = Mock(return_value=timezone.now().replace(hour=23))
    logger.error = Mock()
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 500)
    self.assert_length(mail.outbox, 0)
    logger.error.assert_called_once_with(
      'auto_create_cycles running at unexpected time %s; aborting',
      timezone.now.return_value)

  def test_no_cycles_found(self):
    timezone.now = Mock(return_value=timezone.now().replace(hour=8))
    logger.info = Mock()
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 0)
    logger.info.assert_called_once_with(
        'auto_create_cycles found no recently closed cycles')

  def test_both(self):
    fake_now = timezone.now().replace(hour=8) + timedelta(days=1)
    rr_cycle = factories.GrantCycle(
      title='Rapid Response',
      open=fake_now - timedelta(weeks=2),
      close=fake_now - timedelta(minutes=4)
    )
    s_cycle = factories.GrantCycle(
      title='Seed Grant',
      open=fake_now - timedelta(weeks=2),
      close=fake_now - timedelta(minutes=95)
    )
    self.assert_count(models.GrantCycle.objects.all(), 2)

    for i in range(0, 4):
      factories.DraftGrantApplication(grant_cycle=s_cycle if i % 2 else rr_cycle)

    logger.info = Mock()
    timezone.now = Mock(return_value=fake_now)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 201)

    logger.info.assert_any_call('auto_create_cycles created %d new cycles', 2)
    new_cycle_ids = (models.GrantCycle.objects
        .filter(close__gte=fake_now)
        .values_list('id', flat=True))

    for draft in models.DraftGrantApplication.objects.all():
      self.assertIn(draft.grant_cycle_id, new_cycle_ids)

    for c_id in new_cycle_ids:
      self.assert_count(models.CycleNarrative.objects.filter(
        grant_cycle_id=c_id), len(gc.STANDARD_NARRATIVES)
      )
    self.assert_length(mail.outbox, 1)

  def test_already_created(self):
    fake_now = timezone.now().replace(hour=8) + timedelta(days=1)
    timezone.now = Mock(return_value=fake_now)
    logger.info = Mock()

    cycle = factories.GrantCycle(
      title='Rapid Response',
      open=fake_now - timedelta(weeks=2),
      close=fake_now - timedelta(hours=1)
    )
    factories.DraftGrantApplication(grant_cycle=cycle)
    cycle = factories.GrantCycle(
      title='Rapid Response',
      open=fake_now - timedelta(minutes=5),
      close=fake_now + timedelta(days=12)
    )

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(logger.info.call_count, 2)
    logger.info.assert_any_call(
      'auto_create_cycles skipping %s cycle; next one exists', 'Rapid Response')
    logger.info.assert_any_call(
      'auto_create_cycles did nothing; new cycles already existed')
    self.assert_count(models.GrantCycle.objects.all(), 2)
    self.assert_length(mail.outbox, 0)
