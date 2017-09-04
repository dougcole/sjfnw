from unittest import skip

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from sjfnw.grants import views
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.models import (DraftGrantApplication, GrantApplication,
    Organization, ProjectApp, GrantApplicationLog, GivingProjectGrant,
    NarrativeAnswer, SponsoredProgramGrant)

@skip("Needs additional fixtures") #TODO
class AdminInlines(BaseGrantTestCase):
  """ Verify basic display of related inlines for grants objects in admin """

  def setUp(self): # don't super, can't set cycle dates with this fixture
    self.login_as_admin()

  def test_organization(self):
    """ Verify that related inlines show existing objs """

    app = GrantApplication.objects.first()

    res = self.client.get('admin:grants_organization/{}/'.format(app.organization_id))

    self.assertContains(res, app.grant_cycle.title)
    self.assertContains(res, app.pre_screening_status)

  def test_givingproject(self):
    """ Verify that projectapps are shown as inlines """

    papp = ProjectApp.objects.first()

    res = self.client.get(reverse('admin:fund_givingproject_change', papp.giving_project_id))

    self.assertContains(res, unicode(papp.application.organization))

  def test_application(self):
    """ Verify that gp assignment and awards are shown on application page """

    papp = ProjectApp.objects.first()

    res = self.client.get('admin:grants_grantapplication/{}/'.format(papp.application_id))

    self.assertContains(res, papp.giving_project.title)
    self.assertContains(res, papp.screening_status)


class AdminRevert(BaseGrantTestCase):

  def setUp(self):
    super(AdminRevert, self).setUp()
    self.login_as_admin()

  def _get_url(self, app_id):
    return reverse('revert_app', kwargs={'app_id': app_id})

  def test_load_revert(self):
    app = factories.GrantApplication()

    res = self.client.get(self._get_url(app.pk))

    self.assertEqual(200, res.status_code)
    self.assertContains(res, 'Are you sure you want to revert this application into a draft?')

  def test_revert_app(self):
    app = factories.GrantApplication()

    answers = (NarrativeAnswer.objects
        .filter(grant_application=app)
        .values('cycle_narrative__narrative_question__name', 'text'))
    a = {}
    for ans in answers:
      a[ans['cycle_narrative__narrative_question__name']] = ans['text']

    self.client.post(self._get_url(app.pk))

    self.assert_count(
      GrantApplication.objects.filter(organization_id=app.organization_id),
      0)
    draft = DraftGrantApplication.objects.get(
        organization_id=app.organization_id, grant_cycle_id=app.grant_cycle_id)
    self.assert_draft_matches_app(draft, app, a)


class AdminRollover(BaseGrantTestCase):

  url = reverse('admin_rollover', kwargs={'app_id': 1})

  def setUp(self):
    super(AdminRollover, self).setUp()
    self.login_as_admin()

  def test_unknown_app(self):
    res = self.client.post(reverse('admin_rollover', kwargs={'app_id': 101}))
    self.assertEqual(res.status_code, 404)

  def test_unknown_cycle(self):
    source_app = factories.GrantApplication()
    res = self.client.post(
      reverse('admin_rollover', kwargs={'app_id': source_app.pk}),
      data={'cycle': 99}
    )
    self.assertEqual(res.status_code, 200)
    self.assertIn('Select a valid choice', res.context['form'].errors['cycle'][0])

  def test_app_exists(self):
    source_app = factories.GrantApplication()
    target_cycle = factories.GrantCycle(status='open')
    app = factories.GrantApplication(
      organization=source_app.organization, grant_cycle=target_cycle)

    res = self.client.post(
      reverse('admin_rollover', kwargs={'app_id': source_app.pk}),
      data={'cycle': target_cycle.pk}
    )
    self.assertEqual(res.status_code, 200)
    self.assertFalse(res.context['form'].is_valid())
    self.assert_count(GrantApplication.objects.filter(grant_cycle_id=target_cycle.pk), 1)

  def test_draft_exists(self):
    source_app = factories.GrantApplication()
    draft = factories.DraftGrantApplication(
      organization=source_app.organization, grant_cycle__status='open')
    res = self.client.post(
      reverse('admin_rollover', kwargs={'app_id': source_app.pk}),
      data={'cycle': draft.grant_cycle.pk}
    )

    self.assertEqual(res.status_code, 200)
    self.assertFalse(res.context['form'].is_valid())
    self.assert_count(GrantApplication.objects.filter(grant_cycle=draft.grant_cycle), 0)

  def test_cycle_closed(self):
    """ Admin can rollover into closed cycle """
    source_app = factories.GrantApplication()
    target_cycle = factories.GrantCycle(status='closed')
    res = self.client.post(
      reverse('admin_rollover', kwargs={'app_id': source_app.pk}),
      data={'cycle': target_cycle.pk}
    )
    self.assertEqual(res.status_code, 302)
    self.assertRegexpMatches(res.get('Location'), r'/admin/grants/grantapplication/\d+/$')
    self.assert_count(GrantApplication.objects.filter(grant_cycle=target_cycle), 1)

  def test_cycle_open(self):
    source_app = factories.GrantApplication()
    target_cycle = factories.GrantCycle(status='open')
    res = self.client.post(
      reverse('admin_rollover', kwargs={'app_id': source_app.pk}),
      data={'cycle': target_cycle.pk}
    )
    self.assertEqual(res.status_code, 302)
    self.assertRegexpMatches(res.get('Location'), r'/admin/grants/grantapplication/\d/$')
    self.assert_count(GrantApplication.objects.filter(grant_cycle=target_cycle), 1)

class MergeOrgs(BaseGrantTestCase):

  admin_url = reverse('admin:grants_organization_changelist')

  def setUp(self):
    super(MergeOrgs, self).setUp()
    self.login_as_admin()

  def test_action_available(self):
    factories.Organization() # need at least 1 org to exist for actions to appear

    res = self.client.get(self.admin_url, follow=True)
    self.assertContains(res, '<option value="merge"')

  def test_start_single_org(self):
    org = factories.Organization()

    post_data = {
      'action': 'merge',
      '_selected_action': [org.pk]
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/change_list.html')
    self.assert_message(res, 'Merge can only be done on two organizations. You selected 1.')

  def test_start_triple_org(self):

    a = factories.Organization()
    b = factories.Organization()
    c = factories.Organization()

    post_data = {
      'action': 'merge',
      '_selected_action': [a.pk, b.pk, c.pk]
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/change_list.html')
    self.assert_message(res, 'Merge can only be done on two organizations. You selected 3.')

  def test_start_conflicting_drafts(self):
    a = factories.Organization()
    b = factories.Organization()

    # create drafts for same cycle
    draft_a = factories.DraftGrantApplication(organization=a)
    draft_b = factories.DraftGrantApplication(organization=b,
                                              grant_cycle=draft_a.grant_cycle)

    post_data = {'action': 'merge', '_selected_action': [a.pk, b.pk]}
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/change_list.html')
    self.assert_message(res, r'same grant cycle. Cannot be automatically merged.$', regex=True)

  def test_start_conflicting_apps(self):
    a = factories.Organization()
    b = factories.Organization()

    # create apps for same cycle
    app_a = factories.GrantApplication(organization=a)
    app_b = factories.GrantApplication(organization=b,
                                       grant_cycle=app_a.grant_cycle)

    post_data = {'action': 'merge', '_selected_action': [a.pk, b.pk]}
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/change_list.html')
    self.assert_message(res, r'same grant cycle. Cannot be automatically merged.$', regex=True)

  def test_start_valid_one_empty(self):
    a = factories.Organization()
    b = factories.OrganizationWithProfile()

    post_data = {
      'action': 'merge',
      '_selected_action': [a.pk, b.pk]
    }
    res = self.client.post(self.admin_url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/grants/merge_orgs.html')
    self.assertContains(res, a.name)
    self.assertContains(res, b.name)

  def test_merged_one_sided(self):
    a = factories.Organization()
    b = factories.Organization()
    factories.GrantApplication.create_batch(2, organization=b)
    factories.DraftGrantApplication.create_batch(2, organization=b)

    url = reverse('merge_orgs', kwargs={'id_a': a.pk, 'id_b': b.pk})
    post_data = {'primary': a.pk}
    res = self.client.post(url, post_data, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'admin/change_form.html')
    self.assert_message(res, 'Merge successful. Redirected to new organization page')

    # secondary org & user should have been deleted
    self.assert_count(Organization.objects.filter(pk=b.pk), 0)
    self.assert_count(User.objects.filter(username=b.user.username), 0)

    log = (GrantApplicationLog.objects.filter(organization=a)
                                      .order_by('-date')
                                      .first())
    self.assertIsNotNone(log)
    self.assertRegexpMatches(log.notes, r'^Merged')

    self.assert_count(GrantApplication.objects.filter(organization_id=a.pk), 2)
    self.assert_count(DraftGrantApplication.objects.filter(organization_id=a.pk), 2)

  @skip('TODO')
  def test_merge_both_have_objs(self):
    cycles = factories.GrantCycle.create_batch(5)

    a = factories.Organization()
    factories.GrantApplication.create_batch(2, organization=a)
    factories.SponsoredProgramGrant(organization=a)

    b = factories.Organization()
    app = factories.GrantApplication(organization=b)

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

    url = reverse('merge_orgs', kwargs={'id_a': sec, 'id_b': primary})
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
