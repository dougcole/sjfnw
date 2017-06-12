from datetime import timedelta
import logging

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

from sjfnw import constants as c, utils
from sjfnw.grants.models import DraftGrantApplication, GivingProjectGrant, GrantCycle

logger = logging.getLogger('sjfnw')


def auto_create_cycles(request):
  now = timezone.now()

  if now.hour != 0:
    logger.error('auto_create_cycles running at unexpected time %s; aborting', now)
    return HttpResponse(status=500)

  cycles = GrantCycle.objects.filter(
    Q(title__startswith='Rapid Response') | Q(title__startswith='Seed '),
    close__range=(now - timedelta(hours=2), now)
  )

  if len(cycles) == 0:
    logger.info('auto_create_cycles found no recently closed cycles')
    return HttpResponse(status=200)

  created = 0
  for cycle in cycles:
    prefix = 'Rapid Response' if cycle.get_type() == 'rapid' else 'Seed Grant'

    if GrantCycle.objects.filter(title__startswith=prefix, close__gte=now).exists():
      logger.info('auto_create_cycles skipping %s cycle; next one exists', prefix)
      continue

    # cache original cycle before overwriting fields
    prev_cycle = {
      'id': cycle.pk,
      'title': cycle.title
    }
    cycle.id = None
    cycle.open = timezone.now()
    cycle.close = cycle.close + timedelta(days=14)

    cycle.title = '{} {}.{}.{} - {}.{}.{}'.format(
      prefix,
      cycle.open.month, cycle.open.day, cycle.open.year,
      cycle.close.month, cycle.close.day, cycle.close.year,
    )
    cycle.save()

    created += 1

    # add some context for use in email

    cycle.prev_cycle = prev_cycle
    cycle.drafts_count = (DraftGrantApplication.objects
        .filter(grant_cycle_id=prev_cycle['id'])
        .update(grant_cycle_id=cycle.id))

  if created > 0:
    logger.info('auto_create_cycles created %d new cycles', created)

    utils.send_email(
      subject='Grant cycles created',
      sender=c.GRANT_EMAIL,
      to=['aisapatino@gmail.com'],
      template='grants/emails/auto_create_cycles.html',
      context={'cycles': cycles}
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


def yer_reminder_email(request):
  """ Remind orgs of upcoming year end reports that are due
      NOTE: Must run exactly once a day. ONLY SUPPORTS UP TO 2-YEAR GRANTS
      Sends reminder emails at 1 month and 1 week """

  today = timezone.now().date()

  # get awards due in 7 or 30 days
  year_ago = today.replace(year=today.year - 1)
  reminder_deltas = [timedelta(days=7), timedelta(days=30)]
  award_dates = []
  for delta in reminder_deltas:
    award_dates.append(today + delta)
    award_dates.append((today + delta).replace(year=today.year - 1))

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
