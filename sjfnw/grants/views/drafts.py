import json, logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from sjfnw.decorators import login_required_ajax
from sjfnw.grants.decorators import registered_org
from sjfnw.grants.forms import RolloverForm
from sjfnw.grants.models import DraftGrantApplication, GrantApplication, GrantCycle
from sjfnw.grants.utils import get_user_override

logger = logging.getLogger('sjfnw')
LOGIN_URL = '/apply/login/'


@login_required_ajax(login_url=LOGIN_URL)
@registered_org()
def autosave_app(request, organization, cycle_id):
  """ Save non-file fields to a draft """

  cycle = get_object_or_404(GrantCycle, pk=cycle_id)
  draft = get_object_or_404(DraftGrantApplication,
      organization=organization, grant_cycle=cycle)

  if request.method == 'POST':
    curr_user = request.POST.get('user_id')

    # check for simultaneous editing
    if request.GET.get('force') != 'true':
      if draft.recently_edited():
        if draft.modified_by and draft.modified_by != curr_user:
          # last save wasn't this userid
          logger.info('Requiring confirmation')
          return HttpResponse('confirm force', status=409)
    else:
      logger.info('Force - skipped check')

    logger.debug('Autosaving')
    draft.contents = json.dumps(request.POST)
    draft.modified = timezone.now()
    draft.modified_by = curr_user or 'none'
    draft.save()
    return HttpResponse('success')

@require_http_methods(['DELETE'])
@registered_org()
def discard_draft(request, organization, draft_id):
  try:
    saved = DraftGrantApplication.objects.get(pk=draft_id)
  except DraftGrantApplication.DoesNotExist:
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
def copy_app(request, organization):

  if request.method == 'POST':
    form = RolloverForm(organization, request.POST)
    if form.is_valid():
      cycle_id = form.cleaned_data.get('cycle')
      draft = form.cleaned_data.get('draft')
      app_id = form.cleaned_data.get('application')

      # get cycle
      try:
        cycle = GrantCycle.objects.get(pk=int(cycle_id))
      except GrantCycle.DoesNotExist:
        logger.warning('copy_app GrantCycle %d not found', cycle_id)
        return render(request, 'grants/copy_app_error.html')

      # make sure the combo does not exist already
      if DraftGrantApplication.objects.filter(
          organization=organization, grant_cycle=cycle).exists():
        logger.warning('copy_app the combo already exists!?')
        return render(request, 'grants/copy_app_error.html')

      # get app/draft and its contents (json format for draft)
      if app_id:
        try:
          application = GrantApplication.objects.get(pk=int(app_id))
          draft = DraftGrantApplication.objects.create_from_submitted_app(application, save=False)
          draft.grant_cycle = cycle
          draft.save()
        except GrantApplication.DoesNotExist:
          logger.warning('copy_app - submitted app %s not found', app_id)
      elif draft:
        try:
          draft = DraftGrantApplication.objects.get(pk=int(draft))
          DraftGrantApplication.objects.copy(draft, cycle.pk)
        except DraftGrantApplication.DoesNotExist:
          logger.warning('copy_app - draft %s not found', draft)
      else:
        logger.warning('copy_app no draft or app...')
        return render(request, 'grants/copy_app_error.html')

      return redirect('/apply/' + cycle_id + get_user_override(request))

    else: # INVALID FORM
      logger.info('Invalid form: %s', form.errors)
      cycle_count = str(form['cycle']).count('<option value') - 1
      apps_count = (str(form['application']).count('<option value') +
                    str(form['draft']).count('<option value') - 2)

  else: # GET
    form = RolloverForm(organization)
    cycle_count = str(form['cycle']).count('<option value') - 1
    apps_count = (str(form['application']).count('<option value') +
                  str(form['draft']).count('<option value') - 2)

  return render(request, 'grants/org_app_copy.html',
                {'form': form, 'cycle_count': cycle_count, 'apps_count': apps_count})
