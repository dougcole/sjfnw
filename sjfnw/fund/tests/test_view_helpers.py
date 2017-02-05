import logging

from django.contrib.auth.models import User

from sjfnw.fund import models
from sjfnw.fund.views import _create_membership
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')
TEST_EMAIL = 'testemail124@gmail.com'

class CreateUser(BaseFundTestCase):

  def test_user_exists(self):
    User.objects.create_user(TEST_EMAIL, 'pass')

    try:
      member = models.Member.objects.create_with_user(
          email=TEST_EMAIL, password='pass',
          first_name='anna luisa', last_name='patino')

    except ValueError as err:
      self.assertRegexpMatches(err.message, 'already registered')

    self.assert_count(models.Member.objects.filter(user__username=TEST_EMAIL), 0)

  def test_success(self):
    self.assert_count(User.objects.filter(email=TEST_EMAIL), 0)

    member = models.Member.objects.create_with_user(
        email=TEST_EMAIL, password='pass',
        first_name='anna luisa', last_name='patino')

    self.assertIsInstance(member, models.Member)
    self.assertIsInstance(member.user, User)


class CreateMembership(BaseFundTestCase):

  def test_already_exists(self):
    gp = models.GivingProject.objects.get(title='Pre training')
    member = models.Member.objects.create_with_user(
        email=TEST_EMAIL, first_name='A', last_name='P')
    member.save()
    existing_ship = models.Membership(member=member, giving_project=gp)
    existing_ship.save()

    membership, error = _create_membership(member, gp)

    self.assertRegexpMatches(error, 'already registered')
    self.assertEqual(membership, existing_ship, msg='Returns the pre-existing membership')

  def test_valid(self):
    gp = models.GivingProject.objects.get(title='Pre training')
    member = models.Member.objects.create_with_user(
        email=TEST_EMAIL, password='pass',
        first_name='A', last_name='P')

    membership, error = _create_membership(member, gp)

    self.assertIsNone(error)
    self.assertIsInstance(membership, models.Membership)
    self.assertFalse(membership.approved)

  def test_pre_approved(self):
    gp = models.GivingProject.objects.get(title='Pre training')
    gp.pre_approved = TEST_EMAIL
    gp.save()
    member = models.Member.objects.create_with_user(
        email=TEST_EMAIL, password='pass',
        first_name='A', last_name='P')

    membership, error = _create_membership(member, gp)

    self.assertIsNone(error)
    self.assertIsInstance(membership, models.Membership)
    self.assertTrue(membership.approved)
