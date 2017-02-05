from datetime import timedelta
import logging

from django.utils import timezone

from sjfnw.fund import models
from sjfnw.tests.base import BaseTestCase

logger = logging.getLogger('sjfnw')


class BaseFundTestCase(BaseTestCase):

  fixtures = ['sjfnw/fund/fixtures/test_fund.json']

  def __init__(self, *args, **kwargs):
    super(BaseFundTestCase, self).__init__(*args, **kwargs)
    self.known_members['current'] = 'testacct@gmail.com'
    self.known_members['new'] = 'newacct@gmail.com'

  def setUp(self):
    self.create_projects()

  def create_projects(self):
    """ Create pre- and post-training giving projects """
    today = timezone.now()
    gp = models.GivingProject(title="Post training", fund_goal=5000,
        fundraising_training=today - timedelta(days=10),
        fundraising_deadline=today + timedelta(days=80))
    gp.save()
    gp = models.GivingProject(title="Pre training", fund_goal=10000,
        fundraising_training=today + timedelta(days=10),
        fundraising_deadline=today + timedelta(days=30))
    gp.save()

  def login_as_member(self, name):
    """ Expands on method from BaseTestCase, adding additional members """

    super(BaseFundTestCase, self).login_as_member(name)

    if hasattr(self, 'member_id'): # member was set up in super call
      return

    member = models.Member.objects.create_with_user(email=self.email, password='pass',
                                                    first_name=name, last_name='Member')
    self.setup_member(member)
    self.login_strict(self.email, 'pass')

  def setup_member(self, member):
    self.member_id = member.pk

    post_gp = models.GivingProject.objects.get(title="Post training")
    post_ship = models.Membership(giving_project=post_gp, member=member, approved=True)
    post_ship.save()

    if member.first_name == 'current':
      self.ship_id = post_ship.pk
      member.current = post_ship.pk
      member.save()

      # create donor & step
      donor = models.Donor(membership=post_ship, firstname='Anna', amount=500,
                           talked=True, likelihood=50)
      donor.save()
      step = models.Step(donor=donor, description='Talk to about project',
                         created=timezone.now(), date='2013-04-06')
      step.save()
      self.donor_id = donor.pk
      self.step_id = step.pk

    elif member.first_name == 'new':
      self.post_id = post_ship.pk

      pre_gp = models.GivingProject.objects.get(title='Pre training')
      pre_ship = models.Membership(giving_project=pre_gp, member=member, approved=True)
      pre_ship.save()
      self.pre_id = self.ship_id = pre_ship.pk

      member.current = pre_ship.pk
      member.save()

    else:
      raise Exception('setup_member got unexpected name: {}'.format(member.first_name))
