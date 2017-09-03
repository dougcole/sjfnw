import logging

from unittest import skip

from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')

class AdminHome(BaseFundTestCase):

  def setUp(self):
    super(AdminHome, self).setUp()
    self.login_as_admin()

  def test_home(self):
    response = self.client.get('/admin', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['title'], None)
    self.assertEqual(len(response.context['app_list']), 4)

  def test_fund_home(self):
    response = self.client.get('/admin/fund/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['title'], 'Fundraising administration')
    self.assertEqual(len(response.context['app_list']), 1)


class AdminGivingProjects(BaseFundTestCase):

  fixtures = [
    'sjfnw/fund/fixtures/giving_projects.json',
    'sjfnw/fund/fixtures/members.json',
    'sjfnw/fund/fixtures/memberships.json',
    'sjfnw/fund/fixtures/donors.json',
    'sjfnw/fund/fixtures/resources.json',
    'sjfnw/fund/fixtures/project_resources.json'
  ]

  def setUp(self):
    super(AdminGivingProjects, self).setUp()
    self.login_as_admin()

  def test_giving_projects(self):
    response = self.client.get('/admin/fund/givingproject/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['module_name'], u'giving projects')
    self.assertIn('choices', response.context)


@skip
class AdminMembershipRelated(BaseFundTestCase):

  fixtures = [
    'sjfnw/fund/fixtures/lg_gp.json',
    'sjfnw/fund/fixtures/lg_member.json',
    'sjfnw/fund/fixtures/lg_membership.json',
    'sjfnw/fund/fixtures/lg_donor.json'
  ]

  def setUp(self):
    super(AdminMembershipRelated, self).setUp()
    self.login_as_admin()

  def test_memberships(self):
    response = self.client.get('/admin/fund/membership/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['module_name'], u'memberships')
    self.assertIn('choices', response.context)

  def test_donors(self):
    response = self.client.get('/admin/fund/donor/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['module_name'], u'donors')
    self.assertIn('choices', response.context)


@skip
class AdminResources(BaseFundTestCase):

  fixtures = [
    'sjfnw/fund/fixtures/lg_gp.json',
    'sjfnw/fund/fixtures/lg_resource.json',
    'sjfnw/fund/fixtures/lg_proj_resource.json'
  ]

  def setUp(self):
    super(AdminResources, self).setUp()
    self.login_as_admin()

  def test_resource(self):
    response = self.client.get('/admin/fund/resource/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['module_name'], u'resources')


@skip
class AdminMisc(BaseFundTestCase):

  fixtures = ['sjfnw/fund/fixtures/lg_gp.json']

  def setUp(self):
    super(AdminMisc, self).setUp()
    self.login_as_admin()

  def test_news_items(self):
    response = self.client.get('/admin/fund/newsitem/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['module_name'], u'news items')
    self.assertIn('choices', response.context)

  def test_surveys(self):
    response = self.client.get('/admin/fund/survey/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['module_name'], u'surveys')

  def test_survey_responses(self):
    response = self.client.get('/admin/fund/surveyresponse/', follow=True)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context['module_name'], u'survey responses')
    self.assertIn('choices', response.context)
