from datetime import timedelta
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from sjfnw.grants import models
from sjfnw.grants.forms.org_tools import RolloverForm
from sjfnw.grants.decorators import registered_org

logger = logging.getLogger('sjfnw')

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

@login_required(login_url=LOGIN_URL)
@registered_org()
def copy_app(request, organization):

  if request.method == 'POST':
    form = RolloverForm(organization, request.POST)
    if form.is_valid():
      cycle_id = form.cleaned_data.get('cycle')
      draft_id = form.cleaned_data.get('draft')
      app_id = form.cleaned_data.get('application')

      # get cycle
      try:
        cycle = models.GrantCycle.objects.get(pk=int(cycle_id))
      except models.GrantCycle.DoesNotExist:
        logger.warning('copy_app GrantCycle %d not found', cycle_id)
        return render(request, 'grants/copy_app_error.html')

      # make sure the combo does not exist already
      if organization.has_app_or_draft(cycle.pk):
        logger.warning('Org already has draft or app for selected cycle')
        return render(request, 'grants/copy_app_error.html')

      # get app/draft and its contents (json format for draft)
      if app_id:
        try:
          source = models.GrantApplication.objects.get(pk=int(app_id))
        except models.GrantApplication.DoesNotExist:
          logger.warning('Application %s not found', app_id)
          return render(request, 'grants/copy_app_error.html')
      elif draft_id:
        try:
          source = models.DraftGrantApplication.objects.get(pk=int(draft_id))
        except models.DraftGrantApplication.DoesNotExist:
          logger.warning('Draft %s not found', draft_id)
          return render(request, 'grants/copy_app_error.html')
      else:
        logger.warning('No source draft or app selected for rollover')
        return render(request, 'grants/copy_app_error.html')

      if not _is_valid_rollover_target(source, cycle):
        logger.warning('Cannot rollover into different cycle type')
        return render(request, 'grants/copy_app_error.html')

      if app_id:
        draft = models.DraftGrantApplication.objects.create_from_submitted_app(source)
        draft.grant_cycle = cycle
        draft.save()
      elif draft_id:
        models.DraftGrantApplication.objects.copy(source, cycle.pk)

      return redirect('/apply/' + cycle_id + get_user_override(request))

    else: # INVALID FORM
      logger.info('Invalid form: %s', form.errors)

  else: # GET
    form = RolloverForm(organization)

  cycle_count = str(form['cycle']).count('<option value') - 1
  apps_count = (str(form['application']).count('<option value') +
                str(form['draft']).count('<option value') - 2)

  return render(request, 'grants/org_app_copy.html', {
    'form': form, 'cycle_count': cycle_count, 'apps_count': apps_count
  })

@require_http_methods(['DELETE'])
@registered_org()
def discard_draft(request, organization, draft_id):
  try:
    saved = models.DraftGrantApplication.objects.get(pk=draft_id)
  except models.DraftGrantApplication.DoesNotExist:
    return HttpResponse(status=404)
  else:
    if saved.organization != organization:
      logger.warning(u'Failed attempt to discard draft %s by %s', draft_id, organization)
      return HttpResponse(status=400, content='User does not have permission to delete this draft')
    saved.delete()
    logger.info('Draft %s  discarded', draft_id)
    return HttpResponse('success')


@login_required(login_url=LOGIN_URL)
@registered_org()
def rollover_yer(request, organization):

  error_msg = ''

  # get reports and grants related to current org
  reports = models.YearEndReport.objects.select_related().filter(
      award__projectapp__application__organization_id=organization.pk)
  if reports:
    drafts = models.YERDraft.objects.select_related().filter(
        award__projectapp__application__organization_id=organization.pk)

    award_reports = {}
    for report in reports:
      if report.award_id in award_reports:
        award_reports[report.award_id] += 1
      else:
        award_reports[report.award_id] = 1
    for draft in drafts:
      if draft.award_id in award_reports:
        award_reports[draft.award_id] += 1
      else:
        award_reports[draft.award_id] = 1

    raw_awards = (models.GivingProjectGrant.objects
        .select_related('projectapp__application__organization')
        .filter(projectapp__application__organization_id=organization.pk))
    awards = []
    for award in raw_awards:
      if (award.pk not in award_reports) or (award_reports[award.pk] < award.grant_length()):
        awards.append(award)

    if not awards:
      if raw_awards:
        error_msg = ('You have a submitted or draft year-end report for all '
                     'of your grants. <a href="/apply">Go back</a>')
      else:
        error_msg = 'You don\'t have any other grants that require a year-end report.'
  else:
    error_msg = 'You don\'t have any submitted reports to copy.'

  if error_msg != '': # show error page whether it's get or post
    return render(request, 'grants/yer_rollover.html', {'error_msg': error_msg})

  if request.method == 'POST':
    form = RolloverYERForm(reports, awards, request.POST)
    if form.is_valid():
      report_id = form.cleaned_data.get('report')
      award_id = form.cleaned_data.get('award')

      award = get_object_or_404(models.GivingProjectGrant, pk=award_id)
      report = get_object_or_404(models.YearEndReport, pk=report_id)

      # make sure combo doesn't already exist
      if hasattr(award, 'yearendreport') or models.YERDraft.objects.filter(award_id=award_id):
        logger.error('Valid YER rollover but award has draft/YER already')
        error_msg = 'Sorry, that grant already has a draft or submitted year-end report.'
        return render(request, 'grants/yer_rollover.html', {'error_msg': error_msg})

      contents = model_to_dict(report, exclude=[
        'modified', 'submitted', 'photo1', 'photo2', 'photo3', 'photo4', 'photo_release'])
      contact = contents['contact_person'].split(', ', 1)
      # manually convert db value to multiwidget values #TODO
      contents['contact_person_0'] = contact[0]
      contents['contact_person_1'] = contact[1]
      logger.debug(contents)
      new_draft = models.YERDraft(award=award, contents=json.dumps(contents))
      new_draft.photo1 = report.photo1
      new_draft.photo2 = report.photo2
      new_draft.photo3 = report.photo3
      new_draft.photo4 = report.photo4
      new_draft.photo_release = report.photo_release
      new_draft.save()
      return redirect(reverse('sjfnw.grants.views.year_end_report',
                              kwargs={'award_id': award_id}))
    else: # INVALID FORM
      logger.error('Invalid YER rollover. %s', form.errors)
      return render(request, 'grants/yer_rollover.html', {
        'error_msg': 'Invalid selection. Retry or contact an admin for assistance.'
      })

  else: # GET
    form = RolloverYERForm(reports, awards)
    return render(request, 'grants/yer_rollover.html', {'form': form})
