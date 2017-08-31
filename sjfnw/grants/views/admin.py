import logging

from django.shortcuts import render, get_object_or_404, redirect

from sjfnw.grants import models
from sjfnw.grants.forms.admin import AdminRolloverForm, LoginAsOrgForm, OrgMergeForm

logger = logging.getLogger('sjfnw')

def revert_app_to_draft(request, app_id):
  """ Turn a submitted application back into a draft by creating a
    DraftGrantApplication with all of its content and then deleting the
    GrantApplication.
  """

  submitted_app = get_object_or_404(models.GrantApplication, pk=app_id)

  if request.method == 'POST':
    draft = models.DraftGrantApplication.objects.create_from_submitted_app(submitted_app)
    submitted_app.delete()
    draft.save()
    logger.info('Reverted to draft, draft id %s', draft.pk)

    return redirect('/admin/grants/draftgrantapplication/' + str(draft.pk) + '/')

  return render(request, 'admin/grants/confirm_revert.html', {'application': submitted_app})

def admin_rollover(request, app_id):
  """ Copy a GrantApplication into another grant cycle """

  application = get_object_or_404(models.GrantApplication, pk=app_id)
  org = application.organization

  if request.method == 'POST':
    form = AdminRolloverForm(org, request.POST)
    if form.is_valid():
      cycle = get_object_or_404(models.GrantCycle, pk=int(form.cleaned_data['cycle']))
      application.pk = None # this + save makes new copy
      application.pre_screening_status = 10
      application.submission_time = timezone.now()
      application.grant_cycle = cycle
      application.budget = ''
      application.save()
      # TODO narratives
      logger.info(u'Successful rollover of %s to %s', application, cycle)
      return redirect('/admin/grants/grantapplication/' + str(application.pk) + '/')
  else:
    form = AdminRolloverForm(org)

  cycle_count = str(form['cycle']).count('<option value')

  return render(request, 'admin/grants/rollover.html', {
    'form': form, 'application': application, 'count': cycle_count
  })

def show_yer_statuses(request):
  awards = (models.GivingProjectGrant.objects
    .filter(agreement_mailed__isnull=False)
    .select_related('projectapp__application__organization', 'projectapp__giving_project')
    .order_by('agreement_mailed'))
  yers = models.YearEndReport.objects.values_list('award_id', flat=True)
  # count submitted yers by award id
  yers_by_award = {}
  for award_id in yers:
    award_id = str(award_id)
    if award_id in yers_by_award:
      yers_by_award[award_id] = yers_by_award[award_id] + 1
    else:
      yers_by_award[award_id] = 1
  # set count on award object and add computed properties
  for award in awards:
    if str(award.pk) in yers_by_award:
      award.yer_count = yers_by_award[str(award.pk)]
    else:
      award.yer_count = 0
    award.complete = award.yer_count >= award.grant_length()
    next_due = award.next_yer_due()
    award.past_due = next_due and next_due < timezone.now().date()

  return render(request, 'admin/grants/yer_status.html', {'awards': awards})

def login_as_org(request):

  if request.method == 'POST':
    form = LoginAsOrgForm(request.POST)
    if form.is_valid():
      org = form.cleaned_data['organization']
      return redirect('/apply/?user=' + org)
  form = LoginAsOrgForm()
  return render(request, 'admin/grants/impersonate.html', {'form': form})

def _merge_conflict(a, b):
  cycles = {}

  # check for conflicts
  for appset in [a.grantapplication_set.all(), a.draftgrantapplication_set.all(),
                 b.grantapplication_set.all(), b.draftgrantapplication_set.all()]:
    for app in appset:
      if app.grant_cycle_id in cycles:
        return True
      else:
        cycles[app.grant_cycle_id] = True

def merge_orgs(request, id_a, id_b):

  org_a = (models.Organization.objects
        .prefetch_related('grantapplication_set', 'draftgrantapplication_set')
        .get(pk=id_a))
  org_b = (models.Organization.objects
        .prefetch_related('grantapplication_set', 'draftgrantapplication_set')
        .get(pk=id_b))

  error = ''
  cycles = {}

  if _merge_conflict(org_a, org_b):
    messages.error(request,
      'Orgs have a draft or submitted application for the same grant cycle.'
      ' Cannot be automatically merged.')
    return redirect(reverse('admin:grants_organization_changelist'))

  if request.method == 'POST':
    form = OrgMergeForm(org_a, org_b, request.POST)

    if form.is_valid():

      primary_id = int(request.POST['primary'])

      if primary_id == org_a.pk:
        primary = org_a
        sec = org_b
      elif primary_id == org_b.pk:
        primary = org_b
        sec = org_a
      else:
        logger.error('Primary org (%s) is not one of originals (%s, %s)',
          primary_id, org_a.pk, org_b.pk)
        messages.error(request, 'Something went wrong; unable to merge.')
        return redirect(reverse('admin:grants_organization_changelist'))

      # check whether secondary has most recent app - org profile needs to be updated
      if sec.grantapplication_set.exists():
        sec_latest = sec.grantapplication_set.first()
        primary_latest = primary.grantapplication_set.first()
        if not primary_latest or (primary_latest.submission_time < sec_latest.submission_time):
          primary.update_profile(sec_latest)

      # transfer related objects
      sec.grantapplication_set.update(organization_id=primary.pk)
      sec.draftgrantapplication_set.update(organization_id=primary.pk)
      sec.sponsoredprogramgrant_set.update(organization_id=primary.pk)
      sec.grantapplicationlog_set.update(organization_id=primary.pk)

      note = models.GrantApplicationLog(organization=primary, staff=request.user,
          notes='Merged organization {} into this organization.'.format(sec.name))
      note.save()

      logger.info('Post-merge, deleting organization %s and associated User', sec.name)
      if sec.user:
        sec.user.delete()
      sec.delete()

      messages.success(request, 'Merge successful. Redirected to new organization page')
      return redirect(reverse('admin:grants_organization_change', args=(primary.pk,)))

  else: # GET
    form = OrgMergeForm(org_a, org_b)

  return render(request, 'admin/grants/merge_orgs.html', {
    'orgs': [org_a, org_b],
    'form': form
  })
