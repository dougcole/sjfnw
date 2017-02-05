# coding: utf8

from django.test import TestCase
from django.utils import timezone

from sjfnw.fund.models import GivingProject, Member, Membership

class ModelUnicodes(TestCase):

  def test_unicode(self):
    """ Verify that unicode methods work for Member, GP and Membership """
    project = GivingProject(title=u'Â Fake Giving Project',
                            fundraising_training=timezone.now(),
                            fundraising_deadline=timezone.now())
    project.save()
    member = Member.objects.create_with_user(first_name='Al', last_name=u'Fiüsher',
                                             email='zzz@zz.zz', password='n')
    membership = Membership(giving_project=project, member=member)
    self.assertEqual(u'Al Fiüsher', unicode(member))
    self.assertEqual(u'Â Fake Giving Project %d' % timezone.now().year, unicode(project))
    self.assertEqual(u'Al Fiüsher, Â Fake Giving Project %d' % timezone.now().year,
                     unicode(membership))
