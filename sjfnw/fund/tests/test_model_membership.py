import logging

from django.utils import timezone

from sjfnw.fund.models import Membership, Donor, Step
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')

class GetProgress(BaseFundTestCase):

  def setUp(self):
    super(GetProgress, self).setUp()
    self.login_as_member('new')

  def test_none(self):
    membership = Membership.objects.get(pk=self.pre_id)
    progress = membership.get_progress()
    self.assertEqual(progress['estimated'], 0)
    self.assertEqual(progress['promised'], 0)
    self.assertEqual(progress['received_this'], 0)
    self.assertEqual(progress['received_next'], 0)
    self.assertEqual(progress['received_afternext'], 0)
    self.assertEqual(progress['received_total'], 0)

  def test_multiple_received(self):
    donor = Donor(membership_id=self.pre_id, firstname='Sally', amount=40,
                  likelihood=75, asked=True, promised=40, received_this=40)
    donor.save()
    donor = Donor(membership_id=self.pre_id, firstname='Diego', amount=200,
                  likelihood=50, asked=True, promised=300, received_this=100,
                  received_next=100)
    donor.save()

    membership = Membership.objects.get(pk=self.pre_id)
    progress = membership.get_progress()
    self.assertEqual(progress['estimated'], 130)
    self.assertEqual(progress['promised'], 340)
    self.assertEqual(progress['received_this'], 140)
    self.assertEqual(progress['received_next'], 100)
    self.assertEqual(progress['received_afternext'], 0)
    self.assertEqual(progress['received_total'], 240)


class UpdateStory(BaseFundTestCase):

  def setUp(self):
    super(UpdateStory, self).setUp()
    self.login_as_member('current')
    self.membership = Membership.objects.get(pk=self.ship_id)
    self.name = self.membership.member.first_name # used in many of these tests

    # assert that each test starts without an existing news story
    story_count = self.membership.newsitem_set.count()
    self.assertEqual(story_count, 0)

  def test_nothing(self):
    self.membership.update_story(timezone.now())
    story_count = self.membership.newsitem_set.count()
    self.assertEqual(story_count, 0)

  def test_talk(self):
    now = timezone.now()
    step = Step(donor_id=self.donor_id, date=now, description='Talk to this person')
    step.completed = now
    step.save()

    self.membership.update_story(timezone.now())

    stories = self.membership.newsitem_set.all()
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(story.summary, u'{} talked to 1 person.'.format(self.name))

  def test_ask(self):
    now = timezone.now()
    step = Step(donor_id=self.donor_id, date=now, description='Talk to this person')
    step.completed = now
    step.asked = True
    step.save()

    self.membership.update_story(timezone.now())

    stories = self.membership.newsitem_set.all()
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(story.summary, u'{} asked 1 person.'.format(self.name))

  def test_ask_with_promise(self):
    now = timezone.now()
    step = Step(donor_id=self.donor_id, date=now, description='Talk to this person')
    step.completed = now
    step.asked = True
    step.promised = 50
    step.save()

    self.membership.update_story(timezone.now())

    stories = self.membership.newsitem_set.all()
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(story.summary, u'{} asked 1 person and got $50 in promises.'.format(self.name))

  def test_talk_with_promise(self):
    now = timezone.now()
    step = Step(donor_id=self.donor_id, date=now, description='Talk to this person')
    step.completed = now
    step.promised = 50
    step.save()

    self.membership.update_story(timezone.now())

    stories = self.membership.newsitem_set.all()
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(story.summary, u'{} talked to 1 person and got $50 in promises.'.format(self.name))

  def test_multiple_same_donor(self):
    now = timezone.now()
    step = Step(donor_id=self.donor_id, date=now, description='Talk to this person')
    step.completed = now
    step.save()

    step = Step(donor_id=self.donor_id, date=now, description='Follow up')
    step.completed = now
    step.save()

    self.membership.update_story(timezone.now())

    stories = self.membership.newsitem_set.all()
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(story.summary, u'{} talked to 1 person.'.format(self.name))

  def test_combo(self):
    now = timezone.now()
    step = Step(donor_id=self.donor_id, date=now, description='Talk to this person')
    step.completed = now
    step.save()

    step = Step(donor_id=self.donor_id, date=now, description='Follow up')
    step.completed = now
    step.save()

    donor2 = Donor(membership_id=self.membership.pk, firstname='ADA')
    donor2.save()

    step = Step(donor_id=donor2.pk, date=now, description='Ask this other person')
    step.completed = now
    step.asked = True
    step.promised = 150
    step.save()

    donor3 = Donor(membership_id=self.membership.pk, firstname='Uncle so and so')
    donor3.save()

    step = Step(donor_id=donor3.pk, date=now, description='Ask for $$$')
    step.completed = now
    step.promised = 500
    step.save()

    self.membership.update_story(timezone.now())

    stories = self.membership.newsitem_set.all()
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(story.summary,
        u'{} talked to 2 people, asked 1 and got $650 in promises.'.format(self.name))
