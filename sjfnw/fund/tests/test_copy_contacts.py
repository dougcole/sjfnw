import logging

from django.core.urlresolvers import reverse

from sjfnw.fund import models
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')


class CopyContacts(BaseFundTestCase):

  get_url = reverse('sjfnw.fund.views.home')
  post_url = reverse('sjfnw.fund.views.copy_contacts')
  template = 'fund/forms/copy_contacts.html'

  def setUp(self):
    super(CopyContacts, self).setUp()
    self.login_as_member('first')

    # create a new empty membership and set as member.current
    pre = models.GivingProject.objects.get(title='Pre training')
    membership = models.Membership(giving_project=pre, member_id=self.member_id,
                                   approved=True)
    membership.save()
    self.membership = membership
    member = models.Member.objects.get(pk=self.member_id)
    member.current = membership.pk
    member.save()

  def test_no_duplicates(self):
    """ Verify that form display & submits properly without dup contacts

    Setup:
      Use a member that has existing contacts
      Create fresh membership
      Go to home page

    Asserts:
      After post, number of donors associated with membership = number in form
    """

    res = self.client.get(self.get_url, follow=True)

    self.assertTemplateUsed(res, self.template)
    formset = res.context['formset']
    self.assert_count(
      models.Donor.objects.filter(membership__member_id=self.member_id),
      formset.initial_form_count()
    )
    self.assert_count(models.Donor.objects.filter(membership=self.membership), 0)

    post_data = {'form-MAX_NUM_FORMS': 1000}
    post_data['form-INITIAL_FORMS'] = formset.initial_form_count()
    post_data['form-TOTAL_FORMS'] = formset.initial_form_count()
    index = 0
    for contact in formset.initial:
      post_data['form-%d-email' % index] = contact['email']
      post_data['form-%d-firstname' % index] = contact['firstname']
      post_data['form-%d-lastname' % index] = contact['lastname']
      post_data['form-%d-email' % index] = contact['email']
      post_data['form-%d-notes' % index] = contact['notes']
      post_data['form-%d-select' % index] = 'on'
      index += 1

    res = self.client.post(self.post_url, post_data)

    # compare donors in form to *current* membership's donors
    self.assert_count(
      models.Donor.objects.filter(membership=self.membership),
      formset.initial_form_count()
    )

  def test_merge_duplicates(self):
    """ Verify that duplicate contacts are merged before form is displayed

      Add duplicates in all 3 ways (last, phone, email).
    """
    unique_donors = models.Donor.objects.filter(membership__member_id=self.member_id).count()
    self.assertEqual(unique_donors, 8)

    # match by first + last name, add notes
    copy = models.Donor(membership_id=self.ship_id, firstname="Lyn", lastname="Long",
                        notes="An alliterative fellow.")
    copy.save()
    # match by first + email
    copy = models.Donor(membership_id=self.ship_id, firstname="Nate",
                        email="nat@yahoo.com")
    copy.save()
    # match by first + phone, add last name
    copy = models.Donor(membership_id=self.ship_id, firstname="Patice", lastname="Attison",
                        phone="555-555-8956")
    copy.save()

    res = self.client.get(self.get_url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, self.template)

    formset = res.context['formset']
    self.assertEqual(formset.initial_form_count(), unique_donors)

    self.assertContains(res, 'Lyn', 1)
    self.assertContains(res, 'Patice', 1)
    self.assertContains(res, 'Nate', 1)
    self.assertContains(res, 'An alliterative fellow')
    self.assertContains(res, 'Attison')

  def test_skip(self):
    # verify that copy contacts shows up
    self.assertFalse(self.membership.copied_contacts)
    res = self.client.get(self.get_url, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(self.template)

    # post a skip
    res = self.client.post(self.post_url, {'skip': 'True'})

    # show that it was marked on membership and the form is not triggered again
    membership = models.Membership.objects.get(pk=self.membership.pk)
    self.assertTrue(membership.copied_contacts)
    res = self.client.get(self.get_url, follow=True)
    self.assertTemplateNotUsed(self.template)
