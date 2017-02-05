from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.fund import models
from sjfnw.fund.views import _compile_membership_progress
from sjfnw.fund.tests.base import BaseFundTestCase

class AddContacts(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.home')

  def setUp(self):
    super(AddContacts, self).setUp()
    self.login_as_member('new')

  def test_new(self):
    """ Verify that add mult form is shown to new memberships """

    # using pre-training membership

    membership = models.Membership.objects.get(pk=self.pre_id)

    response = self.client.get(self.url, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')
    self.assertEqual(response.context['request'].membership, membership)
    self.assertNotContains(response, 'likelihood')

    # using post-training membership

    member = models.Member.objects.get(pk=self.member_id)
    member.current = self.post_id
    member.save()
    membership = models.Membership.objects.get(pk=self.post_id)

    response = self.client.get(self.url, follow=True)

    self.assertTemplateUsed(response, 'fund/forms/add_contacts.html')
    self.assertEqual(response.context['request'].membership, membership)
    self.assertContains(response, 'likelihood')

  def test_contacts_without_est(self):
    """ Going to home page with contacts that do not have estimates """

    # using pre-training membership
    membership = models.Membership.objects.get(pk=self.pre_id)

    # create contacts without amount or likelihood
    contact1 = models.Donor(firstname='Anna', membership=membership)
    contact1.save()
    contact2 = models.Donor(firstname='Banana', membership=membership)
    contact2.save()

    response = self.client.get(self.url)

    # verify estimates form is not shown
    self.assertEqual(response.context['request'].membership, membership)
    self.assertTemplateNotUsed('fund/forms/add_estimates.html')

    # using post-training membership
    member = membership.member
    member.current = self.post_id
    member.save()

    membership = models.Membership.objects.get(pk=self.post_id)

    # move created contacts to current membership
    contact1.membership = membership
    contact1.save()
    contact2.membership = membership
    contact2.save()

    response = self.client.get(self.url, follow=True)

    # verify estimates form is shown
    self.assertTemplateUsed('fund/forms/add_estimates.html')
    self.assertEqual(response.context['request'].membership, membership)

class AddEstimates(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.home')

  def setUp(self):
    super(AddEstimates, self).setUp()
    self.login_as_member('new')

  def test_estimates_done(self):
    """ Verify add estimates form is not shown if contacts have estimates """

    # use post-training membership
    membership = models.Membership.objects.get(pk=self.post_id)
    member = membership.member
    member.current = self.post_id
    member.save()

    # create contacts with amount & likelihood
    contact = models.Donor(firstname='Anna', membership=membership, amount=0, likelihood=0)
    contact.save()
    contact = models.Donor(firstname='Banana', membership=membership, amount=567, likelihood=34)
    contact.save()

    response = self.client.get(self.url)

    # verify estimates form is not shown
    self.assertTemplateNotUsed('fund/forms/add_estimates.html')
    self.assertEqual(response.context['request'].membership, membership)


class HomeSurveys(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.home')

  def setUp(self):
    super(HomeSurveys, self).setUp()
    self.login_as_member('current')
    survey = models.Survey(title='First Meeting')
    survey.save()
    self.survey_id = survey.pk
    gp = models.GivingProject.objects.get(title='Post training')
    gpsurvey = models.GPSurvey(survey_id=survey.pk, giving_project=gp,
                               date=timezone.now())
    gpsurvey.save()

  def test_survey_shown(self):
    membership = models.Membership.objects.get(pk=self.ship_id)
    self.assertEqual(membership.completed_surveys, '[]')

    response = self.client.get(self.url, follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'fund/forms/gp_survey.html')

  def test_surveys_complete(self):
    membership = models.Membership.objects.get(pk=self.ship_id)
    membership.completed_surveys = '[{}]'.format(self.survey_id)
    membership.save()

    response = self.client.get(self.url, follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateNotUsed(response, 'fund/forms/gp_survey.html')


class CompileMembershipProgress(BaseFundTestCase):
  """ Test _compile_membership_progress method used by home view """

  def test_empty(self):
    progress, incomplete_steps = _compile_membership_progress([])

    self.assertEqual(incomplete_steps, [])
    for _, value in progress.iteritems():
      self.assertEqual(value, 0)

  def test_basic(self):
    # membership with a few donors, some progress
    self.login_as_member('new')
    ship_id = self.post_id

    # first donor
    donor = models.Donor(membership_id=ship_id, firstname='Alice',
                         amount=240, likelihood=75, talked=True)
    donor.save()
    step = models.Step(donor=donor, date='2015-04-01',
                       description='Talk', completed='2015-04-01')
    step.save()
    step = models.Step(donor=donor, date='2015-5-25', description='Ask')
    step.save()

    # second donor
    donor = models.Donor(membership_id=ship_id, firstname='Bab', talked=True,
                         amount=300, likelihood=50, asked=True,
                         promised=300, received_this=100, received_next=100)
    donor.save()
    step = models.Step(donor=donor, date='2015-04-01',
                       description='Ask', completed='2015-04-01', asked=True)
    step.save()
    step = models.Step(donor=donor, date='2015-04-08',
                       description='Follow upt', completed='2015-04-08',
                       promised=300)
    step.save()
    step = models.Step(donor=donor, date='2015-5-25', description='Thank')
    step.save()

    donors = models.Donor.objects.filter(membership_id=ship_id).prefetch_related('step_set')

    progress, incomplete_steps = _compile_membership_progress(donors)

    self.assertIsInstance(progress, dict)
    self.assertEqual(progress['estimated'], 330)
    self.assertEqual(progress['contacts'], 2)
    self.assertEqual(progress['asked'], 1)
    self.assertEqual(progress['talked'], 1)
    self.assertEqual(progress['promised'], 100)
    self.assertEqual(progress['received'], 200)

    self.assertEqual(progress['contacts_remaining'], 0)
    self.assertEqual(progress['togo'], 30)

    self.assertEqual(len(incomplete_steps), 2)
    for donor in donors:
      self.assertIsInstance(donor.next_step, models.Step)
      self.assertIs(type(donor.completed_steps), list)
      self.assertTrue(len(donor.completed_steps) > 0)


class FormQueryParams(BaseFundTestCase):
  """
  The logic for loading the forms is in the javascript - all we can test is that
  the url query params are passed into the template via context.
  """
  url = reverse('sjfnw.fund.views.home')

  def setUp(self):
    super(FormQueryParams, self).setUp()
    self.login_as_member('current')

  def test_add_mult_step(self):
    res = self.client.get(self.url + '?load=stepmult')

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/home.html')
    self.assertEqual(res.context['load'], reverse('sjfnw.fund.views.add_mult_step'))
    self.assertEqual(res.context['loadto'], 'addmult')

  def test_edit_step(self):
    url = self.url + '?donor={}&step={}&t=edit'.format(self.donor_id, self.step_id)
    res = self.client.get(url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/home.html')
    expected_load_url = reverse(
        'sjfnw.fund.views.edit_step',
        kwargs={'donor_id': self.donor_id, 'step_id': self.step_id})
    self.assertEqual(res.context['load'], expected_load_url)
    self.assertEqual(res.context['loadto'], '{}-nextstep'.format(self.donor_id))

  def test_complete_step(self):
    url = self.url + '?t=complete&donor={}&step={}'.format(self.donor_id, self.step_id)
    res = self.client.get(url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/home.html')
    expected_load_url = reverse(
        'sjfnw.fund.views.complete_step',
        kwargs={'donor_id': self.donor_id, 'step_id': self.step_id})
    self.assertEqual(res.context['load'], expected_load_url)
    self.assertEqual(res.context['loadto'], '{}-nextstep'.format(self.donor_id))
