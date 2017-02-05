from datetime import timedelta
import logging

from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.fund.models import Member, Membership, GivingProject
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')

LOGIN_URL = reverse('sjfnw.fund.views.fund_login')
MANAGE_ACCOUNT_URL = reverse('sjfnw.fund.views.manage_account')
HOME_URL = reverse('sjfnw.fund.views.home')
NOT_MEMBER_URL = reverse('sjfnw.fund.views.not_member')

class SetCurrent(BaseFundTestCase):

  def setUp(self):
    super(SetCurrent, self).setUp()
    self.login_as_member('current')

  def test_not_logged_in(self):
    self.client.logout()

    url = reverse('sjfnw.fund.views.set_current', kwargs={'ship_id': '888'})
    res = self.client.get(url)

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, self.BASE_URL + LOGIN_URL + '?next=' + url)

  def test_unknown_id(self):
    url = reverse('sjfnw.fund.views.set_current', kwargs={'ship_id': '888'})
    res = self.client.get(url)

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, self.BASE_URL + MANAGE_ACCOUNT_URL)

  def test_valid(self):
    pre_gp = GivingProject.objects.get(title='Pre training')
    new_ship = Membership(member_id=self.member_id, giving_project=pre_gp, approved=True)
    new_ship.save()

    member = Member.objects.get(pk=self.member_id)
    self.assertNotEqual(member.current, new_ship.pk)

    url = reverse('sjfnw.fund.views.set_current', kwargs={'ship_id': new_ship.pk})

    res = self.client.get(url)

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, self.BASE_URL + HOME_URL)

    member = Member.objects.get(pk=self.member_id)
    self.assertEqual(member.current, new_ship.pk)

class ManageAccount(BaseFundTestCase):

  def test_load_not_logged_in(self):
    res = self.client.get(MANAGE_ACCOUNT_URL)

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url,
        self.BASE_URL + LOGIN_URL + '?next=' + MANAGE_ACCOUNT_URL)

  def test_load_not_member(self):
    self.login_as_admin()

    res = self.client.get(MANAGE_ACCOUNT_URL)

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, self.BASE_URL + NOT_MEMBER_URL)

  def test_load(self):
    self.login_as_member('current')

    now = timezone.now()
    # create GPs that should be hidden
    yesterday = now - timedelta(days=1)
    private_gp = GivingProject(title='Private Group', fundraising_training=yesterday,
                               fundraising_deadline=now + timedelta(days=40),
                               public=False)
    private_gp.save()
    past_gp = GivingProject(title='Ye Olde Projecte', fundraising_training=yesterday,
                            fundraising_deadline=yesterday)
    past_gp.save()

    res = self.client.get(MANAGE_ACCOUNT_URL)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/account_projects.html')

    expected_gps = GivingProject.objects.filter(public=True, fundraising_deadline__gte=now)
    gp_choices = res.context['form'].fields.get('giving_project').choices
    self.assertEqual(len(gp_choices), expected_gps.count() + 1) # 1 blank choice

    gp_ids = [int(choice[0]) for choice in gp_choices if choice[0]]
    self.assertNotIn(private_gp.pk, gp_ids)
    self.assertNotIn(past_gp.pk, gp_ids)

  def test_unknown_gp(self):
    self.login_as_member('current')
    gp_id = 988
    self.assert_count(GivingProject.objects.filter(pk=gp_id), 0)
    membership_count = Membership.objects.filter(member_id=self.member_id).count()

    res = self.client.post(MANAGE_ACCOUNT_URL, {'giving_project': str(gp_id)})

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/account_projects.html')
    self.assertEqual(res.context['form'].errors['giving_project'][0],
        'Select a valid choice. That choice is not one of the available choices.')
    self.assertEqual(Membership.objects.filter(member_id=self.member_id).count(), membership_count)

  def test_already_registered(self):
    self.login_as_member('current')
    gp_id = GivingProject.objects.get(title='Post training').pk
    self.assert_count(
      Membership.objects.filter(member_id=self.member_id, giving_project_id=gp_id), 1)

    res = self.client.post(MANAGE_ACCOUNT_URL, {'giving_project': str(gp_id)})

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/account_projects.html')
    self.assertEqual(res.context['custom_error'],
        'You are already registered with that giving project.')
    self.assert_count(
      Membership.objects.filter(member_id=self.member_id, giving_project_id=gp_id), 1)

  def test_post_valid(self):
    self.login_as_member('current')
    gp_id = GivingProject.objects.get(title='Pre training').pk
    self.assert_count(
      Membership.objects.filter(member_id=self.member_id, giving_project_id=gp_id), 0)

    res = self.client.post(MANAGE_ACCOUNT_URL, {'giving_project': str(gp_id)})

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/registered.html')
    new_membership = Membership.objects.get(member_id=self.member_id, giving_project_id=gp_id)
    self.assertEqual(new_membership.approved, False)

  def test_post_valid_pre_approved(self):
    self.login_as_member('current')
    gp = GivingProject.objects.get(title='Pre training')
    gp.pre_approved += 'testacct@gmail.com'
    gp.save()
    self.assert_count(
      Membership.objects.filter(member_id=self.member_id, giving_project_id=gp), 0)

    res = self.client.post(MANAGE_ACCOUNT_URL, {'giving_project': str(gp.pk)})

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, self.BASE_URL + HOME_URL)
    new_membership = Membership.objects.get(member_id=self.member_id, giving_project_id=gp.pk)
    self.assertEqual(new_membership.approved, True)
    member = Member.objects.get(pk=self.member_id)
    self.assertEqual(member.current, new_membership.pk)

class NotApproved(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.not_approved')

  def test_not_member(self):
    self.login_as_admin()

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, self.BASE_URL + reverse('sjfnw.fund.views.not_member'))

  def test_member(self):
    self.login_as_member('new')

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/not_approved.html')


class Blocked(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.blocked')

  def test_get(self):
    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/blocked.html')
