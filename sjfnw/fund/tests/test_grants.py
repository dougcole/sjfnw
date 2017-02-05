import logging
from unittest import skip

from django.core.urlresolvers import reverse

from sjfnw.fund import models
from sjfnw.fund.tests.base import BaseFundTestCase
from sjfnw.grants.models import ProjectApp

logger = logging.getLogger('sjfnw')

@skip("Needs additional fixtures")
class Grants(BaseFundTestCase):
  """ Grants listing page """

  fixtures = ['sjfnw/fund/fixtures/test_fund.json',
              # TODO replace with valid fixtures
              'sjfnw/grants/fixtures/orgs.json',
              'sjfnw/grants/fixtures/grant_cycles.json',
              'sjfnw/grants/fixtures/apps.json',
              'sjfnw/grants/fixtures/project_apps.json']

  url = reverse('sjfnw.fund.views.grant_list')

  def setUp(self):
    super(Grants, self).setUp()
    self.login_as_member('current')

  def test_grants_display(self):
    """ Verify that assigned grants are shown on grants page """

    ship = models.Membership(giving_project_id=16, member_id=self.member_id, approved=True)
    ship.save()
    models.Member.objects.filter(pk=self.member_id).update(current = ship.pk)

    response = self.client.get(self.url)

    papps = (ProjectApp.objects.filter(giving_project_id=16)
                               .select_related('application', 'application__organization'))
    self.assertNotEqual(papps.count(), 0)
    for papp in papps:
      if papp.application.pre_screening_status == 45:
        self.assertNotContains(response, unicode(papp.application.organization))
      else:
        self.assertContains(response, unicode(papp.application.organization))
