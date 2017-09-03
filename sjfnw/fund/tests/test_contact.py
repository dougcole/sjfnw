from django.core.urlresolvers import reverse

from sjfnw.fund.modelforms import DonorEditForm, DonorPreForm
from sjfnw.fund.models import Donor, Membership
from sjfnw.fund.tests.base import BaseFundTestCase

class EditContact(BaseFundTestCase):

  def setUp(self):
    super(EditContact, self).setUp()
    self.form_data = {
      'phone': '888-888-8888',
      'firstname': 'John',
      'lastname': 'Doe',
      'likelihood': '10',
      'email': 'testacct@gmail.com',
      'notes': 'adifjaoifjdoiajfoa'
    }

  def _get_url(self, donor_id):
    return reverse('fund:edit_contact', kwargs={'donor_id': donor_id})

  def test_get_without_est(self):
    self.login_as_member('new')
    donor = Donor(membership_id=self.pre_id, firstname='Maebe')
    donor.save()

    res = self.client.get(self._get_url(donor.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/forms/edit_contact.html')
    self.assertIsInstance(res.context['form'], DonorPreForm)

  def test_get(self):
    self.login_as_member('current')

    res = self.client.get(self._get_url(self.donor_id))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/forms/edit_contact.html')
    self.assertIsInstance(res.context['form'], DonorEditForm)

  def test_donor_not_found(self):
    self.login_as_member('current')

    res = self.client.post(self._get_url(8888), self.form_data)

    self.assertEqual(res.status_code, 404)

  def test_no_amount(self):
    self.login_as_member('current')

    res = self.client.post(self._get_url(self.donor_id), self.form_data)

    self.assertTemplateUsed(res, 'fund/forms/edit_contact.html')
    self.assertFormError(res, 'form', 'amount', 'This field is required.')

  def test_negative_amount(self):
    self.login_as_member('current')
    self.form_data['amount'] = '-10'

    res = self.client.post(self._get_url(self.donor_id), self.form_data)

    self.assertTemplateUsed(res, 'fund/forms/edit_contact.html')
    self.assertFormError(res, 'form', 'amount', 'Must be greater than or equal to 0.')

  def test_valid_pre(self):
    self.login_as_member('new')
    donor = Donor(membership_id=self.pre_id, firstname='Maebe')
    donor.save()

    res = self.client.post(self._get_url(donor.pk), self.form_data)

    self.assertEqual(res.content, 'success')

  def test_valid(self):
    self.login_as_member('current')
    self.form_data['amount'] = '10'

    res = self.client.post(self._get_url(self.donor_id), self.form_data)

    self.assertEqual(res.content, 'success')

    contact = Donor.objects.get(pk=self.donor_id)
    self.assertEqual(contact.amount, 10)


class DeleteContact(BaseFundTestCase):

  def setUp(self):
    super(DeleteContact, self).setUp()
    self.login_as_member('current')
    # set copied contacts to avoid redirect after delete
    membership = Membership.objects.get(pk=self.ship_id)
    membership.copied_contacts = True
    membership.save()

  def _get_url(self, donor_id):
    return reverse('fund:delete_contact', kwargs={'donor_id': donor_id})

  def test_get_valid(self):
    res = self.client.get(self._get_url(self.donor_id))
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/forms/delete_contact.html')

  def test_success(self):

    donor = Donor.objects.get(pk=self.donor_id)
    self.assertEqual(donor.membership_id, self.ship_id)

    res = self.client.post(self._get_url(self.donor_id), {})

    self.assertEqual(res.status_code, 302)
    self.assertEqual(res.url, reverse('fund:home'))

    donor = Donor.objects.filter(pk=self.donor_id)
    self.assertEqual(len(donor), 0)

  def test_nonexistent(self):
    donor_id = 894
    self.assert_count(Donor.objects.filter(pk=donor_id), 0)

    res = self.client.post(self._get_url(donor_id), {})

    self.assertEqual(res.status_code, 404)

  def test_permission(self):
    """ Verify failure when requesting to delete another membership's contact """

    # switch to newbie account and verify that test donor is not associated with it
    self.login_as_member('new')
    current_membership = Membership.objects.get(pk=self.ship_id)

    donor_id = 1
    donor = Donor.objects.get(pk=donor_id)

    self.assertNotEqual(donor.membership, current_membership)
    self.assertNotEqual(donor.membership.member_id, self.member_id)

    res = self.client.post(self._get_url(donor_id), {})

    self.assertEqual(res.status_code, 404)
