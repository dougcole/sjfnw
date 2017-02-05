from datetime import timedelta
import logging

from django.http import HttpResponse
from django.utils import timezone

from sjfnw import constants as c, utils
from sjfnw.grants.models import DraftGrantApplication, GivingProjectGrant

logger = logging.getLogger('sjfnw')

def draft_app_warning(request):
  """ Warn orgs of impending draft freezes
      NOTE: must run exactly once a day
      Gives 7 day warning if created 7+ days before close, otherwise 3 day warning """

  drafts = DraftGrantApplication.objects.all()
  eight_days = timedelta(days=8)

  for draft in drafts:
    time_left = draft.grant_cycle.close - timezone.now()
    created_delta = draft.grant_cycle.close - draft.created
    if ((created_delta > eight_days and eight_days > time_left > timedelta(days=7)) or
        (created_delta < eight_days and timedelta(days=3) > time_left >= timedelta(days=2))):
      to_email = draft.organization.get_email()

      if not to_email:
        logger.warn('Unable to send draft reminder; org is not registered %d', draft.organization.pk)
        continue

      utils.send_email(
        subject='Grant cycle closing soon',
        sender=c.GRANT_EMAIL,
        to=[to_email],
        template='grants/email_draft_warning.html',
        context={'org': draft.organization, 'cycle': draft.grant_cycle}
      )
      logger.info('Email sent to %s regarding draft application soon to expire', to_email)
  return HttpResponse('')


def yer_reminder_email(request):
  """ Remind orgs of upcoming year end reports that are due
      NOTE: Must run exactly once a day. ONLY SUPPORTS UP TO 2-YEAR GRANTS
      Sends reminder emails at 1 month and 1 week """

  today = timezone.now().date()

  # get awards due in 7 or 30 days
  year_ago = today.replace(year=today.year - 1)
  award_dates = [
      today + timedelta(days=7),
      today + timedelta(days=30),
      year_ago + timedelta(days=7),
      year_ago + timedelta(days=30)
  ]
  awards = GivingProjectGrant.objects.filter(first_yer_due__in=award_dates)

  for award in awards:
    if award.yearendreport_set.count() < award.grant_length():
      app = award.projectapp.application

      to = app.organization.get_email() or app.email_address
      utils.send_email(
        subject='Year end report',
        sender=c.GRANT_EMAIL,
        to=[to],
        template='grants/email_yer_due.html',
        context={
          'award': award,
          'app': app,
          'gp': award.projectapp.giving_project,
          'base_url': c.APP_BASE_URL
        }
      )
      logger.info('YER reminder email sent to %s for award %d', to, award.pk)

  return HttpResponse('success')
