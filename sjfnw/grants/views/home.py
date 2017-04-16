from datetime import timedelta
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from sjfnw.grants import models
from sjfnw.grants.decorators import registered_org
from sjfnw.grants.utils import get_user_override

logger = logging.getLogger('sjfnw')

LOGIN_URL = '/apply/login/'


@login_required(login_url=LOGIN_URL)
@registered_org()
def org_home(request, org):
  """ Home page shows overview of grant cycles and org's apps and drafts """

  submitted = org.grantapplication_set.order_by('-submission_time')
  submitted_by_id = {}
  submitted_cycles = []
  for app in submitted:
    app.awards = []
    submitted_cycles.append(app.grant_cycle.pk)
    submitted_by_id[app.pk] = app

  awards = (models.GivingProjectGrant.objects
      .filter(projectapp__application__in=submitted)
      .select_related('projectapp')
      .prefetch_related('yearendreport_set', 'yerdraft_set'))
  ydrafts = []
  for award in awards:
    submitted_by_id[award.projectapp.application_id].awards.append(award)
    ydrafts += award.yerdraft_set.all()

  drafts = org.draftgrantapplication_set.select_related('grant_cycle')

  cycles = (models.GrantCycle.objects
      .exclude(private=True)
      .filter(close__gt=timezone.now() - timedelta(days=180))
      .order_by('close'))

  closed, current, upcoming = [], [], []
  for cycle in cycles:
    if cycle.pk in submitted_cycles:
      cycle.applied = True

    status = cycle.get_status()
    if status == 'open':
      current.append(cycle)
    elif status == 'closed':
      closed.append(cycle)
    elif status == 'upcoming':
      upcoming.append(cycle)

  return render(request, 'grants/org_home.html', {
    'organization': org,
    'submitted': submitted,
    'drafts': drafts,
    'ydrafts': ydrafts,
    'cycles': cycles,
    'closed': closed,
    'open': current,
    'upcoming': upcoming,
    'user_override': get_user_override(request)
  })
