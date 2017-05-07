import json

from sjfnw.grants import models
from sjfnw.grants.tests import factories
from sjfnw.tests.base import BaseTestCase

# This file provides a base test class and utilities specific to the grants module

class BaseGrantTestCase(BaseTestCase):

  def login_as_org(self, with_profile=False):
    self.org = factories.OrganizationWithProfile() if with_profile else factories.Organization()
    self.login_strict(self.org.user.username, 'password')

  def assert_draft_matches_app(self, draft, app, app_narratives=None):
    """ Assert that app is a superset of draft
        (All draft fields match app, but app may have additional fields)
        Handles conversion of timeline format between the two. """

    draft_contents = json.loads(draft.contents)
    for field, value in draft_contents.iteritems():
      if hasattr(app, field):
        self.assertEqual(unicode(value), unicode(getattr(app, field)))
      elif field.startswith('timeline') or '_references' in field:
        print('Skipping assertion for json field')
      elif app_narratives:
        self.assertEqual(value, app_narratives[field])
      else:
        self.assertEqual(value, app.get_narrative_answer(field),
          msg='Draft narrative answer for "{}" did not match app'.format(field))
    for field in models.GrantApplication.file_fields():
      if hasattr(draft, field):
        self.assertEqual(getattr(draft, field), getattr(app, field))
