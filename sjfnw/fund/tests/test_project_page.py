from django.core.urlresolvers import reverse

from sjfnw.fund.tests.base import BaseFundTestCase

class GivingProjectPage(BaseFundTestCase):

  url = reverse('fund:project_page')

  def setUp(self):
    super(GivingProjectPage, self).setUp()
    self.login_as_member('new')

  def test_basic_load(self):

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/project.html')
