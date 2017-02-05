import logging
from unittest import skip

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from sjfnw.grants.tests.base import BaseGrantTestCase, LIVE_FIXTURES
from sjfnw.grants.models import (DraftGrantApplication, GrantApplication,
    Organization, ProjectApp, GrantApplicationLog, GivingProjectGrant,
    SponsoredProgramGrant)

logger = logging.getLogger('sjfnw')

@skip("Needs additional fixtures")
class AdminInlines(BaseGrantTestCase):
  """ Verify basic display of related inlines for grants objects in admin """

  fixtures = LIVE_FIXTURES

  def setUp(self): # don't super, can't set cycle dates with this fixture
    self.login_as_admin()

  def test_organization(self):
    """ Verify that related inlines show existing objs """

    app = GrantApplication.objects.first()

    res = self.client.get('/admin/grants/organization/{}/'.format(app.organization_id))

    self.assertContains(res, app.grant_cycle.title)
    self.assertContains(res, app.pre_screening_status)

  def test_givingproject(self):
    """ Verify that projectapps are shown as inlines """

    papp = ProjectApp.objects.first()

    res = self.client.get('/admin/fund/givingproject/{}/'.format(papp.giving_project_id))

    self.assertContains(res, unicode(papp.application.organization))

  def test_application(self):
    """ Verify that gp assignment and awards are shown on application page """

    papp = ProjectApp.objects.first()

    res = self.client.get('/admin/grants/grantapplication/{}/'.format(papp.application_id))

    self.assertContains(res, papp.giving_project.title)
    self.assertContains(res, papp.screening_status)


class AdminRevert(BaseGrantTestCase):

  def setUp(self):
    super(AdminRevert, self).setUp()
    self.login_as_admin()

  def test_load_revert(self):

    res = self.client.get('/admin/grants/grantapplication/1/revert')

    self.assertEqual(200, res.status_code)
    self.assertContains(res, 'Are you sure you want to revert this application into a draft?')

  def test_revert_app(self):
    """ scenario: revert submitted app pk1
        verify:
          draft created
          app gone
          draft fields match app (incl cycle, timeline) """

    self.assertEqual(0,
        DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=1).count())
    app = GrantApplication.objects.get(organization_id=2, grant_cycle_id=1)

    self.client.post('/admin/grants/grantapplication/1/revert')

    self.assertEqual(1,
      DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=1).count())
    draft = DraftGrantApplication.objects.get(organization_id=2, grant_cycle_id=1)
    self.assert_draft_matches_app(draft, app)


class AdminRollover(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.admin_rollover', kwargs={'app_id': 1})

  def setUp(self):
    super(AdminRollover, self).setUp()
    self.login_as_admin()

  def test_unknown_app(self):
    res = self.client.post(reverse('sjfnw.grants.views.admin_rollover',
                                        kwargs={'app_id': 101}))
    self.assertEqual(res.status_code, 404)

  def test_unknown_cycle(self):
    res = self.client.post(
      reverse('sjfnw.grants.views.admin_rollover', kwargs={'app_id': 1}),
      data={'cycle': u'99'}
    )
    self.assertEqual(res.status_code, 200)
    self.assertIn('Select a valid choice', res.context['form'].errors['cycle'][0])

  def test_app_exists(self):
    self.assertEqual(GrantApplication.objects.filter(grant_cycle_id=1).count(), 1)
    res = self.client.post(
      reverse('sjfnw.grants.views.admin_rollover', kwargs={'app_id': 2}),
      data={'cycle': u'1'}
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(GrantApplication.objects.filter(grant_cycle_id=1).count(), 1)
    self.assertFalse(res.context['form'].is_valid())

  def test_draft_exists(self):
    self.assertEqual(GrantApplication.objects.filter(grant_cycle_id=3).count(), 0)
    self.assertEqual(DraftGrantApplication.objects.filter(grant_cycle_id=3).count(), 1)
    res = self.client.post(
      reverse('sjfnw.grants.views.admin_rollover', kwargs={'app_id': 2}),
      data={'cycle': u'3'}
    )
    self.assertEqual(res.status_code, 200)
    self.assertEqual(GrantApplication.objects.filter(grant_cycle_id=3).count(), 0)
    self.assertEqual(DraftGrantApplication.objects.filter(grant_cycle_id=3).count(), 1)
    self.assertFalse(res.context['form'].is_valid())

  def test_cycle_closed(self):
    self.assertEqual(GrantApplication.objects.filter(grant_cycle_id=4).count(), 0)
    res = self.client.post(
      reverse('sjfnw.grants.views.admin_rollover', kwargs={'app_id': 2}),
      data={'cycle': u'4'}
    )
    self.assertEqual(res.status_code, 302)
    self.assertEqual(GrantApplication.objects.filter(grant_cycle_id=4).count(), 1)

  def test_cycle_open(self):
    self.assert_count(GrantApplication.objects.filter(grant_cycle_id=2), 0)
    res = self.client.post(
      reverse('sjfnw.grants.views.admin_rollover', kwargs={'app_id': 2}),
      data={'cycle': u'6'}
    )
    self.assertEqual(res.status_code, 302)
    self.assertRegexpMatches(res.get('Location'), r'/admin/grants/grantapplication/\d/$')
    self.assertEqual(GrantApplication.objects.filter(grant_cycle_id=6).count(), 1)

class MergeOrgs(BaseGrantTestCase):

  admin_url = reverse('admin:grants_organization_changelist')

  def setUp(self):
    self.login_as_admin()

  def test_action_available(self):

    res = self.client.get(self.admin_url, follow=True)
    self.assertContains(res, '<option value="merge"')

  def test_start_single_org(self):

    post_data = {
      'action': 'merge',
      '_selected_action': 1
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertTemplateUsed(res, 'admin/grants/organization/change_list.html')
    self.assert_message(res, 'Merge can only be done on two organizations. You selected 1.')

  def test_start_triple_org(self):

    third = Organization.objects.create_with_user(email='third@third.com', name='third')

    post_data = {
      'action': 'merge',
      '_selected_action': [1, 2, third.pk]
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertTemplateUsed(res, 'admin/grants/organization/change_list.html')
    self.assert_message(res, 'Merge can only be done on two organizations. You selected 3.')

  def test_start_conflicting_drafts(self):
    a_pk = 1
    b_pk = 2

    # a has no apps - rules out conflict over apps
    self.assert_count(GrantApplication.objects.filter(organization_id=a_pk), 0)

    # b has draft; create draft for same cycle for a
    self.assert_count(
      DraftGrantApplication.objects.filter(organization_id=b_pk, grant_cycle_id=2), 1)
    draft = DraftGrantApplication(organization_id=a_pk, grant_cycle_id=2)
    draft.save()

    post_data = {
      'action': 'merge',
      '_selected_action': [1, 2]
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertTemplateUsed(res, 'admin/grants/organization/change_list.html')
    self.assert_message(res, r'same grant cycle. Cannot be automatically merged.$', regex=True)

  def test_start_conflicting_apps(self):
    a_pk = 1
    b_pk = 2

    # a has no drafts - rules out conflict over drafts
    self.assert_count(DraftGrantApplication.objects.filter(organization_id=a_pk), 0)

    # b has app; create draft for same cycle for a
    self.assert_count(
      GrantApplication.objects.filter(organization_id=b_pk, grant_cycle_id=5), 1)
    app = GrantApplication(organization_id=a_pk, grant_cycle_id=5,
        founded='1978', budget_last=300, budget_current=600, amount_requested=99)
    app.save()

    post_data = {
      'action': 'merge',
      '_selected_action': [1, 2]
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertTemplateUsed(res, 'admin/grants/organization/change_list.html')
    self.assert_message(res, r'same grant cycle. Cannot be automatically merged.$', regex=True)

  def test_start_valid_one_empty(self):

    post_data = {
      'action': 'merge',
      '_selected_action': [1, 2]
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertTemplateUsed(res, 'admin/grants/merge_orgs.html')
    org1 = Organization.objects.get(pk=1)
    org2 = Organization.objects.get(pk=2)
    self.assertContains(res, org1.name)
    self.assertContains(res, org2.name)

  def test_merged_one_sided(self):
    primary = 1
    primary_org = Organization.objects.get(pk=primary)
    sec = 2
    sec_org = Organization.objects.get(pk=sec)

    # create corresponding Users for both
    user = User(email=sec_org.email, username=sec_org.email)
    user.save()
    user = User(email=primary_org.email, username=primary_org.email)
    user.save()

    # get draft & app IDs that were associated with secondary org
    sec_apps = list(sec_org.grantapplication_set.values_list('pk', flat=True))
    sec_drafts = list(sec_org.draftgrantapplication_set.values_list('pk', flat=True))
    self.assert_length(sec_apps, 2)
    self.assert_length(sec_drafts, 2)

    url = reverse('sjfnw.grants.views.merge_orgs', kwargs={'id_a': sec, 'id_b': primary})
    post_data = {'primary': primary}
    res = self.client.post(url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/change_form.html')
    self.assert_message(res, 'Merge successful. Redirected to new organization page')

    # secondary org & user should have been deleted
    self.assert_count(Organization.objects.filter(pk=sec), 0)
    self.assert_count(User.objects.filter(email=sec_org.email), 0)

    log = (GrantApplicationLog.objects.filter(organization_id=primary)
                                      .order_by('-date')
                                      .first())
    self.assertIsNotNone(log)
    self.assertRegexpMatches(log.notes, r'^Merged')

    updated_apps = GrantApplication.objects.filter(organization_id=primary, pk__in=sec_apps)
    updated_drafts = DraftGrantApplication.objects.filter(
        organization_id=primary, pk__in=sec_drafts)
    self.assert_length(updated_apps, 2)
    self.assert_length(updated_drafts, 2)

  def test_merge_both_have_objs(self):

    primary = 1
    sec = 2
    sec_org = Organization.objects.get(pk=sec)

    # get draft & app IDs that were associated with secondary org
    sec_apps = list(sec_org.grantapplication_set.values_list('pk', flat=True))
    sec_drafts = list(sec_org.draftgrantapplication_set.values_list('pk', flat=True))
    sec_papps = ProjectApp.objects.filter(application__organization_id=sec)
    self.assert_length(sec_apps, 2)
    self.assert_length(sec_drafts, 2)
    self.assert_count(sec_papps, 1)
    sponsored = SponsoredProgramGrant(organization_id=sec, amount=400)
    sponsored.save()

    # create app for primary org
    app = GrantApplication(organization_id=primary, grant_cycle_id=4,
        founded='1998', budget_last=300, budget_current=600, amount_requested=99)
    app.save()
    papp = ProjectApp(application_id=app.pk, giving_project_id=3)
    papp.save()
    gpg = GivingProjectGrant(projectapp_id=papp.pk, amount=199, first_yer_due='2017-01-03')
    gpg.save()

    url = reverse('sjfnw.grants.views.merge_orgs', kwargs={'id_a': sec, 'id_b': primary})
    post_data = {'primary': primary}
    res = self.client.post(url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/change_form.html')
    self.assert_message(res, 'Merge successful. Redirected to new organization page')

    apps = GrantApplication.objects.filter(organization_id=primary)
    drafts = DraftGrantApplication.objects.filter(organization_id=primary)
    papps = ProjectApp.objects.filter(application__organization_id=primary)
    sponsored = SponsoredProgramGrant.objects.filter(organization_id=primary)
    self.assert_length(apps, 3)
    self.assert_length(drafts, 2)
    self.assert_count(papps, 2)
    self.assert_count(sponsored, 1)
