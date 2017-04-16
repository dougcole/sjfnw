import json, logging

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone

from sjfnw import constants as c, utils
from sjfnw.grants import models
from sjfnw.grants.forms import RolloverYERForm
from sjfnw.grants.modelforms import YearEndReportForm
from sjfnw.grants.views import home as home_views
from sjfnw.grants.views.helpers import get_file_urls, get_viewing_permission
from sjfnw.grants.decorators import registered_org
from sjfnw.grants.utils import get_user_override

logger = logging.getLogger('sjfnw')
LOGIN_URL = '/apply/login'

def autosave_yer(request, award_id):
  """ Autosave a YERDraft """

  if not request.user.is_authenticated():
    return HttpResponse(LOGIN_URL, status=401)

  draft = get_object_or_404(models.YERDraft, award_id=award_id)

  if request.method == 'POST':
    draft.contents = json.dumps(request.POST)
    logger.info(draft.contents)
    draft.modified = timezone.now()
    draft.save()
    return HttpResponse('success')

@login_required(login_url=LOGIN_URL)
@registered_org()
def year_end_report(request, organization, award_id):

  # get award, make sure org matches
  award = get_object_or_404(models.GivingProjectGrant, pk=award_id)
  app = award.projectapp.application

  if app.organization_id != organization.pk:
    logger.warning('Trying to edit someone else\'s YER')
    return redirect(home_views.org_home)

  total_yers = models.YearEndReport.objects.filter(award=award).count()
  # check if already submitted
  if total_yers >= award.grant_length():
    logger.warning('Required YER(s) already submitted for this award')
    return redirect(home_views.org_home)

  # get or create draft
  draft, created = models.YERDraft.objects.get_or_create(award=award)
  if request.method == 'POST':
    draft_data = json.loads(draft.contents)
    files_data = model_to_dict(draft, fields=['photo1', 'photo2', 'photo3',
                                              'photo4', 'photo_release'])
    draft_data['award'] = award.pk
    form = YearEndReportForm(draft_data, files_data)
    if form.is_valid():
      yer = form.save()
      draft.delete()

      utils.send_email(
        subject='Year end report submitted',
        template='grants/email_yer_submitted.html',
        sender=c.GRANT_EMAIL,
        to=[yer.email]
      )
      logger.info('YER submission confirmation email sent to %s', yer.email)
      return redirect('/report/submitted')

    else:
      logger.info('Invalid YER:')
      logger.info(form.errors.items())

  else: # GET
    if created:
      initial_data = {'website': app.website, 'sit_website': app.website,
                      'contact_person': app.contact_person + ', ' + app.contact_person_title,
                      'phone': app.telephone_number, 'email': app.email_address}
      logger.info('Created new YER draft')
    else:
      initial_data = json.loads(draft.contents)
      # manually convert multi-widget TODO improve this
      initial_data['contact_person'] = (initial_data.get('contact_person_0', '') +
          ', ' + initial_data.get('contact_person_1', ''))

    form = YearEndReportForm(initial=initial_data)

  file_urls = get_file_urls(request, draft)
  for field, url in file_urls.iteritems():
    if url:
      name = getattr(draft, field).name.split('/')[-1]
      file_urls[field] = ('<a href="' + url + '" target="_blank" title="' +
          name + '">' + name + '</a> [<a onclick="fileUploads.removeFile(\'' +
          field + '\');">remove</a>]')
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  due = award.first_yer_due.replace(year=award.first_yer_due.year + total_yers)
  yer_period = '{:%b %d, %Y} - {:%b %d, %Y}'.format(due.replace(year=due.year - 1), due)

  return render(request, 'grants/yer_form.html', {
    'form': form,
    'org': organization,
    'draft': draft,
    'award': award,
    'file_urls': file_urls,
    'user_override': get_user_override(request),
    'yer_period': yer_period
  })

def view_yer(request, report_id):

  report = get_object_or_404(models.YearEndReport.objects.select_related(), pk=report_id)

  award = report.award
  projectapp = award.projectapp
  if not request.user.is_authenticated():
    perm = 0
  else:
    perm = get_viewing_permission(request.user, projectapp.application)

  if not report.visible and perm < 2:
    return render(request, 'grants/blocked.html', {})

  form = YearEndReportForm(instance=report)

  file_urls = get_file_urls(request, report, printing=False)

  return render(request, 'grants/yer_display.html', {
    'report': report, 'form': form, 'award': award, 'projectapp': projectapp,
    'file_urls': file_urls, 'perm': perm})

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
