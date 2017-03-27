from datetime import timedelta
import json
import logging

from django.core import mail
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from sjfnw.grants import cron, models, views
from sjfnw.grants.tests import factories
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants.tests.test_apply import BaseGrantFilesTestCase

logger = logging.getLogger('sjfnw')

def _get_autosave_url(award_id):
  return reverse(views.autosave_yer, kwargs={'award_id': award_id})

def _get_yer_url(award_id):
  return reverse(views.year_end_report, kwargs={'award_id': award_id})


class YearEndReportHomeLinks(BaseGrantTestCase):

  url = reverse(views.org_home)

  def _assert_link(self, res, award, count=1):
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed('grants/org_home.html')
    self.assertContains(res, '<a href="{}">'.format(_get_yer_url(award.pk)), count=count)

  def setUp(self):
    super(YearEndReportHomeLinks, self).setUp()
    self.login_as_org()

  def test_home_link(self):
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      amount=5000,
      agreement_mailed=timezone.now() - timedelta(days=200),
      first_yer_due=timezone.now() + timedelta(days=9)
    )
    res = self.client.get(self.url)
    self._assert_link(res, award)

  def test_home_link_without_agreement(self):
    """ Link to report is shown even if agreement hasn't been mailed
      (YER due date used to be based on agreement_mailed) """
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      amount=5000,
      first_yer_due=timezone.now() + timedelta(days=90)
    )
    res = self.client.get(self.url)
    self._assert_link(res, award)

  def test_late_home_link(self):
    """ Link to report is shown even if due date has passed """
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      amount=8000,
      first_yer_due=timezone.now() - timedelta(days=20)
    )
    res = self.client.get(self.url)
    self._assert_link(res, award)

  def test_second_home_link(self):
    # make award be two-year
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      amount=8000,
      second_amount=4000,
      first_yer_due=timezone.now() - timedelta(days=20)
    )
    # submit first YER
    first_yer = factories.YearEndReport(award=award)

    res = self.client.get(self.url)

    self._assert_link(res, award)
    self.assertContains(res, 'Year end report</a> submitted', count=1)

  def test_two_completed(self):
    # two year award with both YER submitted
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      amount=8000,
      second_amount=4000,
      first_yer_due=timezone.now() - timedelta(days=200)
    )
    factories.YearEndReport(award=award)
    factories.YearEndReport(award=award)

    res = self.client.get(self.url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed('grants/org_home.html')
    self.assertContains(res, 'Year end report</a> submitted', count=2)
    self.assertNotContains(res, '<a href="{}>'.format(_get_yer_url(award.pk)))


@override_settings(MEDIA_ROOT='sjfnw/grants/tests/media/',
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    FILE_UPLOAD_HANDLERS=('django.core.files.uploadhandler.MemoryFileUploadHandler',))
class YearEndReportForm(BaseGrantFilesTestCase):

  def _test_valid_submit(self, award):
    draft = factories.YERDraft(award=award)

    post_data = {
      'other_comments': 'Some comments',
      'total_size': '500',
      'award': '55',
      'quantitative_measures': 'Measures',
      'major_changes': 'Changes',
      'summarize_last_year': 'It was all right.',
      'other': '',
      'evaluation': 'abc',
      'donations_count': '503',
      'donations_count_prev': '50',
      'collaboration': 'der',
      'user_id': '',
      'phone': '208-861-8907',
      'goal_progress': 'We haven\'t made much progress sorry.',
      'contact_person_1': 'Executive Board Co-Chair',
      'contact_person_0': 'Kria Pry',
      'new_funding': 'None! UGH.',
      'email': 'Idahoc@gmail.com',
      'facebook': '',
      'website': 'www.idossc.org',
      'achieved': 'Achievement awards.',
      'listserve': 'yes yes',
      'stay_informed': '{}'
    }

    # autosave the post_data (page js does that prior to submitting)
    res = self.client.post(_get_autosave_url(draft.award.pk), post_data)
    self.assertEqual(200, res.status_code)

    # confirm draft updated
    draft.refresh_from_db()
    self.assertEqual(json.loads(draft.contents), post_data)

    # add files to draft
    draft.photo1 = 'budget3.png'
    draft.photo2 = 'budget3.png'
    draft.photo_release = 'budget1.docx'
    draft.save()

    self.assert_length(mail.outbox, 0)

    res = self.client.post(_get_yer_url(draft.award.pk), follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed('grants/yer_submitted.html')

    yer = models.YearEndReport.objects.get(award=award)
    self.assertEqual(yer.photo1, draft.photo1)
    self.assertEqual(yer.photo2, draft.photo2)
    self.assertEqual(yer.photo_release, draft.photo_release)

    self.assert_length(mail.outbox, 1)
    email = mail.outbox[0]
    self.assertEqual(email.subject, 'Year end report submitted')
    self.assertEqual(email.to, [yer.email])

  def _test_start(self, award):
    res = self.client.get(_get_yer_url(award.pk))

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/yer_form.html')

    form = res.context['form']
    application = award.projectapp.application

    expected_title = 'Year-end Report for {:%b %d, %Y} - {:%b %d, %Y}'.format(
        award.first_yer_due.replace(year=award.first_yer_due.year - 1), award.first_yer_due)
    self.assertContains(res, expected_title)

    # assert website autofilled from app
    self.assertEqual(form['website'].value(), application.website)

  def setUp(self):
    super(YearEndReportForm, self).setUp()
    self.login_as_org()

  def test_start_report(self):
    award = factories.GivingProjectGrant(projectapp__application__organization=self.org)
    self._test_start(award)

  def test_start_late(self):
    """ Run the start draft test but with a YER that is overdue """
    award = factories.GivingProjectGrant(
      first_yer_due=timezone.now().date() - timedelta(days=30),
      projectapp__application__organization=self.org
    )
    self._test_start(award)

  def test_start_second_report(self):
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      second_amount=8000
    )
    yer = factories.YearEndReport(award=award)

    self.assertFalse(models.YERDraft.objects.filter(award=award).exists())

    res = self.client.get(_get_yer_url(award.pk))

    self.assertTemplateUsed(res, 'grants/yer_form.html')
    expected_title = 'Year-end Report for {:%b %d, %Y} - {:%b %d, %Y}'.format(
        award.first_yer_due, award.first_yer_due.replace(year=award.first_yer_due.year + 1))
    self.assertContains(res, expected_title)

    application = award.projectapp.application
    self.assertEqual(res.context['form']['website'].value(), application.website)
    self.assert_count(models.YERDraft.objects.filter(award=award), 1)

  def test_autosave(self):
    draft = factories.YERDraft(award__projectapp__application__organization=self.org)

    post_data = {
      'summarize_last_year': 'We did soooooo much stuff last year!!',
      'goal_progress': 'What are goals?',
      'total_size': '546 or 547',
      'other_comments': 'All my single ladies'
    }

    res = self.client.post(_get_autosave_url(draft.award.pk), post_data)
    self.assertEqual(res.status_code, 200)
    draft = models.YERDraft.objects.get(award=draft.award)
    self.assertEqual(json.loads(draft.contents), post_data)

  def test_autosave_logged_out(self):
    draft = factories.YERDraft(award__projectapp__application__organization=self.org)

    self.client.logout()

    post_data = {
      'summarize_last_year': 'We did soooooo much stuff last year!!',
      'goal_progress': 'What are goals?',
      'total_size': '546 or 547',
      'other_comments': 'All my single ladies'
    }

    res = self.client.post(_get_autosave_url(draft.award.pk), post_data)
    self.assertEqual(401, res.status_code)

  def test_valid(self):
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      first_yer_due=timezone.now().date() + timedelta(days=10)
    )
    self._test_valid_submit(award)

  def test_valid_late(self):
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      first_yer_due=timezone.now().date() - timedelta(days=10)
    )
    self._test_valid_submit(award)


class YearEndReportReminders(BaseGrantTestCase):

  url = reverse(cron.yer_reminder_email)

  def setUp(self):
    super(YearEndReportReminders, self).setUp()
    self.login_as_admin()

  def test_two_months_prior(self):
    """ Verify reminder is not sent 2 months before report is due """

    # create award where yer is due in 60 days
    award = factories.GivingProjectGrant(
        first_yer_due=timezone.now().date() + timedelta(days=60))

    # verify that email is not sent
    self.assert_length(mail.outbox, 0)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 0)

  def test_first_email(self):
    """ Verify that reminder email gets sent 30 days prior to due date """

    # create award where yer is due in 30 days
    award = factories.GivingProjectGrant(
        first_yer_due=timezone.now().date() + timedelta(days=30))

    # verify that email is not sent
    self.assert_length(mail.outbox, 0)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 1)

  def test_15_days_prior(self):
    """ Verify that no email is sent 15 days prior to due date """

    # create award where yer is due in 15 days
    award = factories.GivingProjectGrant(
        first_yer_due=timezone.now().date() + timedelta(days=15))

    # verify that email is not sent
    self.assert_length(mail.outbox, 0)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 0)

  def test_second_email(self):
    """ Verify that a reminder email goes out 7 days prior to due date """

    # create award where yer is due in 7 days
    award = factories.GivingProjectGrant(
        first_yer_due=timezone.now().date() + timedelta(days=7))

    # verify that email is sent
    self.assert_length(mail.outbox, 0)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 1)

  def test_yer_complete(self):
    """ Verify that an email is not sent if a year-end report has been completed """

    # create award where yer is due in 7 days, with YER completed
    award = factories.GivingProjectGrant(
        first_yer_due=timezone.now().date() + timedelta(days=7))
    yer = factories.YearEndReport(award=award)

    # verify that no more are due
    self.assertEqual(award.next_yer_due(), None)

    # verify that email is not sent
    self.assert_length(mail.outbox, 0)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 0)

  def test_second_yer_reminder(self):
    """ Verify that reminder email is sent if second year end report due"""

    today = timezone.now().date()

    award = factories.GivingProjectGrant(
      first_yer_due=(today + timedelta(days=7)).replace(year=today.year - 1),
      second_amount=9000
    )

    self.assertEqual(award.next_yer_due(), award.first_yer_due)

    # submit first YER
    yer = factories.YearEndReport(award=award)

    # verify that second yer is due in 7 days
    self.assertEqual(award.next_yer_due(), today + timedelta(days=7))

    # verify that email is sent
    self.assert_length(mail.outbox, 0)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 1)

  def test_second_yer_complete(self):
    """ Verify that reminder email is not sent if second year end report completed"""

    today = timezone.now()
    award = factories.GivingProjectGrant(
      first_yer_due=(today + timedelta(days=7)).replace(year=today.year - 1),
      second_amount=9000
    )
    factories.YearEndReport(award=award)
    factories.YearEndReport(award=award)

    self.assertEqual(award.next_yer_due(), None)

    # verify that email is not sent
    self.assert_length(mail.outbox, 0)
    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assert_length(mail.outbox, 0)


class RolloverYER(BaseGrantTestCase):
  """ Test display and function of the rollover feature for YER """

  url = reverse('sjfnw.grants.views.rollover_yer')

  def setUp(self):
    super(RolloverYER, self).setUp()
    self.login_as_org()

  def test_rollover_link(self):
    """ Verify that link shows on home page """

    res = self.client.get(reverse(views.org_home))
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/org_home.html')
    self.assertContains(res, 'rollover a year-end report')

  def test_display_no_awards(self):
    """ Verify correct error msg, no form, if org has no grants """

    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/yer_rollover.html')
    self.assertEqual(res.context['error_msg'],
        'You don\'t have any submitted reports to copy.')

  def test_display_no_reports(self):
    """ Verify error msg, no form if org has grant(s) but no reports """

    factories.GivingProjectGrant(projectapp__application__organization=self.org)

    res = self.client.get(self.url, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/yer_rollover.html')
    self.assertEqual(res.context['error_msg'],
        'You don\'t have any submitted reports to copy.')

  def test_display_all_reports_done(self):
    """ Verify error msg, no form if org has reports for all grants """
    award = factories.GivingProjectGrant(projectapp__application__organization=self.org)
    factories.YearEndReport(award=award)

    res = self.client.get(self.url, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/yer_rollover.html')
    self.assertRegexpMatches(res.context['error_msg'],
        'You have a submitted or draft year-end report for all of your grants')

  def test_display_second_yr_missing(self):
    """ Verify form if org has completed one but not both reports for their grant """
    award = factories.GivingProjectGrant(
      projectapp__application__organization=self.org,
      second_amount=8000
    )
    factories.YearEndReport(award=award)

    res = self.client.get(self.url, follow=True)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/yer_rollover.html')
    self.assertContains(res, 'option value', count=4)
    self.assertContains(res, 'This form lets you')

  def test_display_form(self):
    """ Verify display of form when there is a valid rollover option """

    # create award and YER
    award = factories.GivingProjectGrant(projectapp__application__organization=self.org)
    factories.YearEndReport(award=award)

    # create 2nd award without YER
    award = factories.GivingProjectGrant(projectapp__application__organization=self.org)

    res = self.client.get(self.url, follow=True)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/yer_rollover.html')
    self.assertContains(res, 'option value', count=4)
    self.assertContains(res, 'This form lets you')

  def test_submit(self):
    """ Verify that rollover submit works:
      New draft is created for the selected award
      User is redirected to edit draft """

    # create award and YER
    award = factories.GivingProjectGrant(projectapp__application__organization=self.org)
    report = factories.YearEndReport(award=award)
    # create 2nd award without YER
    award2 = factories.GivingProjectGrant(projectapp__application__organization=self.org)

    self.assertFalse(models.YERDraft.objects.filter(award=award2).exists())

    post_data = {'report': report.pk, 'award': award2.pk}

    res = self.client.post(self.url, post_data)

    self.assertEqual(res.status_code, 302)
    self.assertTrue(res.url.endswith(_get_yer_url(award2.pk)))
    self.assertTrue(models.YERDraft.objects.filter(award=award2).exists())


class ViewYER(BaseGrantTestCase):

  def setUp(self):
    super(ViewYER, self).setUp()

  def test_not_logged_in(self):
    yer = factories.YearEndReport()

    url = reverse(views.view_yer, kwargs={'report_id': yer.pk})
    res = self.client.get(url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/blocked.html')

  def test_org_author(self):
    self.login_as_org()
    yer = factories.YearEndReport(award__projectapp__application__organization=self.org)

    url = reverse(views.view_yer, kwargs={'report_id': yer.pk})
    res = self.client.get(url)

    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'grants/yer_display.html')
