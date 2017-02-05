from datetime import timedelta
import json

from django.contrib.auth.models import User
from django.utils import timezone

from sjfnw.grants import models
from sjfnw.tests.base import BaseTestCase

# This file provides a base test class and utilities specific to the grants module

LIVE_FIXTURES = ['sjfnw/grants/fixtures/users.json',
                 'sjfnw/grants/fixtures/organizations.json',
                 'sjfnw/grants/fixtures/grant_cycles.json']

def set_cycle_dates():
  """ Update grant cycle dates to make sure they have the expected statuses:
      open, open, closed, upcoming, open """

  now = timezone.now()
  ten_days = timedelta(days=10)

  cycle = models.GrantCycle.objects.get(pk=1)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
  twenty_days = timedelta(days=20)
  cycle = models.GrantCycle.objects.get(pk=2)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=3)
  cycle.open = now - twenty_days
  cycle.close = now - ten_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=4)
  cycle.open = now + ten_days
  cycle.close = now + twenty_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=5)
  cycle.open = now - twenty_days
  cycle.close = now + ten_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=6)
  cycle.open = now - twenty_days
  cycle.close = now + ten_days
  cycle.save()

class BaseGrantTestCase(BaseTestCase):

  fixtures = ['sjfnw/grants/fixtures/test_grants.json']

  def setUp(self):
    set_cycle_dates()
    for i, email in enumerate(['neworg@gmail.com', 'testorg@gmail.com']):
      user = User.objects.create_user(email, email, 'pw')
      org = models.Organization.objects.get(pk=i + 1)
      org.user = user
      org.save()

  # see sjfnw/grants/fixtures/README.md for what objects are associated with each org
  def login_as_org(self, name):
    if name == 'new':
      self.org_id = 1
      self.client.login(username='neworg@gmail.com', password='pw')
    elif name == 'test':
      self.org_id = 2
      self.client.login(username='testorg@gmail.com', password='pw')
    else:
      raise ValueError('Unknown org name {}'.format(name))

  def assert_draft_matches_app(self, draft, app, exclude_cycle_q=False):
    """ Assert that app is a superset of draft
        (All draft fields match app, but app may have additional fields)
        Handles conversion of timeline format between the two.

        If exclude_cycle_q is True, verify that draft does not have
        cycle_question field (useful for rollover) """

    draft_contents = json.loads(draft.contents)
    app_timeline = json.loads(app.timeline)
    for field, value in draft_contents.iteritems():
      if 'timeline' in field:
        i = int(field.split('_')[-1])
        self.assertEqual(value, app_timeline[i])
      else:
        self.assertEqual(value, getattr(app, field))
    for field in models.GrantApplication.file_fields():
      if hasattr(draft, field):
        self.assertEqual(getattr(draft, field), getattr(app, field))
    if exclude_cycle_q:
      self.assertNotIn('cycle_question', draft_contents)
