from datetime import timedelta
import logging

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone

from sjfnw import constants as c, utils
from sjfnw.grants.models import DraftGrantApplication, GivingProjectGrant, GrantCycle

logger = logging.getLogger('sjfnw')


def auto_create_cycles(request):
  now = timezone.now()

  if now.hour != 8: # UTC
    logger.error('auto_create_cycles running at unexpected time %s; aborting', now)
    return HttpResponse(status=500)

  cycles = GrantCycle.objects.filter(
    Q(title__startswith='Rapid Response') | Q(title__startswith='Seed '),
    close__range=(now - timedelta(hours=2), now)
  )

  if len(cycles) == 0:
    logger.info('auto_create_cycles found no recently closed cycles')
    return HttpResponse(status=200)

  created = []
  for cycle in cycles:
    prefix = 'Rapid Response' if cycle.get_type() == 'rapid' else 'Seed Grant'

    if GrantCycle.objects.filter(title__startswith=prefix, close__gte=now).exists():
      logger.info('auto_create_cycles skipping %s cycle; next one exists', prefix)
      continue

    title = '{} {}.{}.{} - {}.{}.{}'.format(
      prefix,
      cycle.open.month, cycle.open.day, cycle.open.year,
      cycle.close.month, cycle.close.day, cycle.close.year,
    )
    new_cycle = GrantCycle.objects.copy(cycle, title, timezone.now(), cycle.close + timedelta(days=14))

    # add some context for use in email

    new_cycle.prev_cycle = cycle
    new_cycle.drafts_count = (DraftGrantApplication.objects
        .filter(grant_cycle_id=cycle.id)
        .update(grant_cycle_id=new_cycle.id))

    created.append(new_cycle)


  if len(created) > 0:
    logger.info('auto_create_cycles created %d new cycles', len(created))

    utils.send_email(
      subject='Grant cycles created',
      sender=c.GRANT_EMAIL,
      to=['aisapatino@gmail.com'],
      template='grants/emails/auto_create_cycles.html',
      context={'cycles': created}
    )
    return HttpResponse(status=201)
  else:
    logger.info('auto_create_cycles did nothing; new cycles already existed')
    return HttpResponse()


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


def report_reminder_email(request):
  """ Remind orgs of upcoming grantee reports that are due
      NOTE: Must run exactly once a day. ONLY SUPPORTS UP TO 2-YEAR GRANTS
      Sends reminder emails at 1 month and 1 week """

  today = timezone.now().date()
  seven_days = timedelta(days=7)
  thirty_days = timedelta(days=30)
  award_dates = [today + seven_days, today + thirty_days]

  awards = (GivingProjectGrant.objects
    .filter(
      Q(first_report_due__in=award_dates) | Q(second_report_due__in=award_dates)
    )
    .annotate(report_count=Count('granteereport'))
  )

  for award in awards:
    due = False
    if award.report_count == 0:
      due = award.first_report_due
    elif award.report_count == 1 and award.second_report_due:
      due = award.second_report_due

    if due:
      app = award.projectapp.application

      to = app.organization.get_email() or app.email_address
      utils.send_email(
        subject='Grantee report',
        sender=c.GRANT_EMAIL,
        to=[to],
        template='grants/email_report_due.html',
        context={
          'award': award,
          'app': app,
          'gp': award.projectapp.giving_project,
          'base_url': c.APP_BASE_URL,
          'due_date': due
        }
      )
      logger.info('Grantee report reminder email sent to %s for award %d', to, award.pk)
  return HttpResponse('success')
