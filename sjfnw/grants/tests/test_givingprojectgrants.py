from datetime import timedelta
import logging

from django.utils import timezone

from sjfnw.grants import models
from sjfnw.grants.tests.base import BaseGrantTestCase

logger = logging.getLogger('sjfnw')

class NewGivingProjectGrant(BaseGrantTestCase):
  """ Test GivingProjectGrant model methods """

  def test_minimum_grant_information(self):
    award = models.GivingProjectGrant(projectapp_id=1, amount=5000,
            first_report_due=timezone.now().date())
    award.save()

    self.assertEqual(award.total_amount(), award.amount)
    self.assertEqual(award.next_report_due(), award.first_report_due)
    self.assertEqual(award.grant_length(), 1)

    self.assertEqual(award.check_number, None)
    self.assertEqual(award.check_mailed, None)

    self.assertEqual(award.second_amount, None)
    self.assertEqual(award.second_check_number, None)
    self.assertEqual(award.second_check_mailed, None)

    self.assertEqual(award.agreement_mailed, None)
    self.assertEqual(award.agreement_returned, None)
    self.assertEqual(award.approved, None)
