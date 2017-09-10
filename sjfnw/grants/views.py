from datetime import datetime, timedelta
import json, logging, re, urllib2

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from google.appengine.ext import blobstore

import unicodecsv

from sjfnw import constants as c, utils
from sjfnw.decorators import login_required_ajax
from sjfnw.fund.models import Member
from sjfnw.grants import constants as gc
from sjfnw.grants import models
from sjfnw.grants.decorators import registered_org
from sjfnw.grants.forms import (AdminRolloverForm, LoginAsOrgForm, LoginForm,
   AppReportForm, SponsoredAwardReportForm, GPGrantReportForm, OrgReportForm,
   RegisterForm, RolloverForm, RolloverYERForm, OrgMergeForm)
from sjfnw.grants.modelforms import get_form_for_cycle, YearEndReportForm
from sjfnw.grants.utils import (local_date_str, find_blobinfo,
    get_user_override, format_draft_contents)

logger = logging.getLogger('sjfnw')

LOGIN_URL = '/apply/login/'

# -----------------------------------------------------------------------------
#  Public views
# -----------------------------------------------------------------------------

def org_login(request):
  if request.method == 'POST':
    form = LoginForm(request.POST)
    if form.is_valid():
      email = request.POST['email'].lower()
      password = request.POST['password']
      user = authenticate(username=email, password=password)
      if user:
        if user.is_active:
          login(request, user)
          return redirect(org_home)
        else:
          logger.warning('Inactive org account tried to log in, username: ' + email)
          messages.error(request, 'Your account is inactive. Please contact an administrator.')
      else:
        messages.error(request, 'Your password didn\'t match the one on file. Please try again.')
  else:
    form = LoginForm()
  register = RegisterForm()
  return render(request, 'grants/org_login_register.html', {
      'form': form, 'register': register
  })

def org_register(request):

  if request.method == 'GET':
    register = RegisterForm()

  elif request.method == 'POST':
    register = RegisterForm(request.POST)

    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']
      org_name = request.POST['organization']

      try:
        org = models.Organization.objects.create_with_user(username_email,
            password=password, name=org_name)
      except ValueError as err:
        logger.warning(username_email + ' tried to re-register as org')
        login_link = utils.create_link(reverse('sjfnw.grants.views.org_login'), 'Login')
        messages.error(request, '{} {} instead.'.format(err.message, login_link))

      else:
        user = authenticate(username=username_email, password=password)
        if user:
          if user.is_active:
            login(request, user)
            return redirect(org_home)
          else:
            logger.info('Registration needs admin approval, showing message. ' +
                username_email)
            messages.warning(request, 'You have registered successfully but your account '
            'needs administrator approval. Please contact '
            '<a href="mailto:info@socialjusticefund.org">info@socialjusticefund.org</a>')
        else:
          messages.error(request, 'There was a problem with your registration. '
              'Please <a href=""/apply/support#contact">contact a site admin</a> for assistance.')
          logger.error('Password not working at registration, account:  ' + username_email)

  form = LoginForm()

  return render(request, 'grants/org_login_register.html', {
    'form': form, 'register': register
  })

def org_support(request):
  return render(request, 'grants/org_support.html', {
    'support_email': c.SUPPORT_EMAIL,
    'support_form': c.GRANT_SUPPORT_FORM
  })

def _fetch_cycle_info(url):
  if not re.search(r'https?://(www.)?socialjusticefund.org', url):
    return '<h4>Grant cycle information page could not be loaded</h4>'
  try:
    info_page = urllib2.urlopen(url)
  except (urllib2.URLError, ValueError) as err:
    logger.error('Error fetching cycle info page: %s', err)
    return (
      '<h4>Grant cycle information page could not be loaded</h4>'
      '<p>Try visiting it directly: {}</p>'.format(
        utils.create_link(url, 'grant cycle information', new_tab=True)
      )
    )
  else:
    content = info_page.read()
    # we're getting pages with a known format from socialjusticefund.org
    # these are hacky ways to strip header/footer and make the img urls work
    start = content.find('<div id="content"')
    end = content.find('<!-- /#content')
    if start == -1 or end == -1:
      logger.error('Info page content from %s missing expected content markers', url)
      return ''

    return content[start:end].replace('modules/file/icons', 'static/images')


def cycle_info(request, cycle_id):

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)

  if not cycle.info_page:
    raise Http404

  content = _fetch_cycle_info(cycle.info_page)

  return render(request, 'grants/cycle_info.html', {
    'cycle': cycle, 'content': content
  })

def not_registered(request):

  if not request.user.is_authenticated():
    return redirect(LOGIN_URL)

  username = request.GET.get('user') or request.user.username

  return render(request, 'grants/not_registered.html', {'username': username})

# -----------------------------------------------------------------------------
#  Org home
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
#  Grant application & Year-end report
# -----------------------------------------------------------------------------

def _autofill_draft(draft):
  """ If org has profile information, use it to autofill draft fields
    Returns: indicator of whether draft was updated. """
  if draft.organization.mission:
    org_dict = model_to_dict(draft.organization, exclude=['fiscal_letter'])
    draft.fiscal_letter = draft.organization.fiscal_letter
    draft.contents = json.dumps(org_dict)
    draft.save()
    logger.debug('Autofilled draft %s, %s', draft.organization, draft.grant_cycle)
    return True
  return False


@login_required_ajax(login_url=LOGIN_URL)
@registered_org()
def autosave_app(request, organization, cycle_id):
  """ Save non-file fields to a draft """

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  draft = get_object_or_404(models.DraftGrantApplication,
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

@login_required(login_url=LOGIN_URL)
@registered_org()
def grant_application(request, organization, cycle_id):
  """ Get or submit the whole application form
    The first time an org visits this page, it will redirect to cycle info page.
  """

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)

  filter_by = {'organization': organization, 'grant_cycle': cycle}

  # check for app already submitted
  if models.GrantApplication.objects.filter(**filter_by).exists():
    return render(request, 'grants/already_applied.html', {
      'organization': organization, 'cycle': cycle
    })

  profiled = False

  if request.method == 'POST':
    draft = get_object_or_404(models.DraftGrantApplication, **filter_by)
    if not draft.editable():
      return render(request, 'grants/submitted_closed.html', {'cycle': cycle})

    # application data is not sent in POST request
    # all the grant application data is saved on the DraftGrantApplication
    # and POST request just indicates that they wish to submit it

    # get fields & files from draft
    draft_data = json.loads(draft.contents)
    files_data = model_to_dict(draft, fields=draft.file_fields())

    # add automated fields
    draft_data['organization'] = organization.pk
    draft_data['grant_cycle'] = cycle.pk

    form = get_form_for_cycle(cycle)(cycle, draft_data, files_data)

    if form.is_valid():
      logger.info('Application form valid')

      application = form.save()

      for cn in models.CycleNarrative.objects.filter(grant_cycle=cycle).select_related('narrative_question'):
        text = form.cleaned_data.get(cn.narrative_question.name)
        answer = models.NarrativeAnswer(cycle_narrative=cn, grant_application=application, text=text)
        answer.save()

      to_email = organization.get_email()
      utils.send_email(
        subject='Grant application submitted',
        sender=c.GRANT_EMAIL,
        to=[to_email],
        template='grants/email_submitted.html',
        context={'org': organization, 'cycle': cycle}
      )
      logger.info('Application submitted for %s; confirmation email sent to %s',
        organization.name, to_email)

      draft.delete()

      return redirect('/apply/submitted')

    else: # INVALID SUBMISSION
      logger.info('Application form invalid. Errors for fields: %s',
          ', '.join(form.errors.keys()))

  else: # GET
    draft = models.DraftGrantApplication.objects.filter(**filter_by).first()

    if draft is None:
      if not cycle.is_open():
        return render(request, 'grants/closed.html', {'cycle': cycle})
      if cycle.info_page and not request.GET.get('info'):
        return redirect(reverse(cycle_info, kwargs={'cycle_id': cycle.pk}))

      draft = models.DraftGrantApplication(**filter_by)
      profiled = _autofill_draft(draft)
      if not profiled: # wasn't saved by _autofill_draft
        draft.save()

    else:
      if not draft.editable():
        return render(request, 'grants/closed.html', {'cycle': cycle})
      if draft.contents == '{}': # if draft was created via admin site
        profiled = _autofill_draft(draft)

    draft_contents = json.loads(draft.contents)
    format_draft_contents(draft_contents)
    form = get_form_for_cycle(cycle)(cycle, initial=draft_contents)

  # get draft files
  file_urls = get_file_urls(request, draft)
  link_template = (u'<a href="{0}" target="_blank" title="{1}">{1}</a> '
                   '[<a onclick="fileUploads.removeFile(\'{2}\');">remove</a>]')
  for field, url in file_urls.iteritems():
    if url:
      name = getattr(draft, field).name.split('/')[-1]
      file_urls[field] = link_template.format(url, name, field)
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  return render(request, 'grants/org_app.html', {
    'form': form,
    'cycle': cycle,
    'file_urls': file_urls,
    'draft': draft,
    'profiled': profiled,
    'org': organization,
    'user_override': get_user_override(request),
    'flag': draft.recently_edited() and draft.modified_by
  })

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
    return redirect(org_home)

  total_yers = models.YearEndReport.objects.filter(award=award).count()
  # check if already submitted
  if total_yers >= award.grant_length():
    logger.warning('Required YER(s) already submitted for this award')
    return redirect(org_home)

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

# -----------------------------------------------------------------------------
#  File handling
# -----------------------------------------------------------------------------

def add_file(request, draft_type, draft_id):
  """ Upload a file to a draft
      Called by javascript in application page """

  if draft_type == 'apply':
    draft = get_object_or_404(models.DraftGrantApplication, pk=draft_id)
    logger.debug(u'%s adding a file', draft.organization)

  elif draft_type == 'report':
    draft = get_object_or_404(models.YERDraft, pk=draft_id)
    logger.debug('Adding a file to YER draft %s', draft_id)

  else:
    logger.error('Invalid draft_type %s for add_file', draft_type)
    raise Http404

  # don't remove this without fixing storage to not access body blob_file = False
  logger.debug([request.body])

  blob_file = False
  for key in request.FILES:
    blob_file = request.FILES[key]
    if blob_file:
      if hasattr(draft, key):
        setattr(draft, key, blob_file)
        field_name = key
        break
      else:
        logger.error('Tried to add an unknown file field ' + str(key))
  draft.modified = timezone.now()
  draft.save()

  if not (blob_file and field_name):
    return HttpResponse('ERROR') # TODO use status code

  file_urls = get_file_urls(request, draft)
  content = (field_name + u'~~<a href="' + file_urls[field_name] +
             u'" target="_blank" title="' + unicode(blob_file) + u'">' +
             unicode(blob_file) + u'</a> [<a onclick="fileUploads.removeFile(\'' +
             field_name + u'\');">remove</a>]')
  logger.info(u'add_file returning: ' + content)
  return HttpResponse(content)

def remove_file(request, draft_type, draft_id, file_field):
  """ Remove file from draft by setting that field to empty string

      Note: does not delete file from Blobstore, since it could be used
        in other drafts/apps
  """
  if draft_type == 'report':
    draft_model = models.YERDraft
  elif draft_type == 'apply':
    draft_model = models.DraftGrantApplication
  else:
    logger.error('Unknown draft type %s', draft_type)
    return HttpResponseBadRequest('Unknown draft type')

  draft = get_object_or_404(draft_model, pk=draft_id)

  if hasattr(draft, file_field):
    setattr(draft, file_field, '')
    draft.modified = timezone.now()
    draft.save()
  else:
    logger.error('Tried to remove non-existent field: ' + file_field)
  return HttpResponse('success')

def get_upload_url(request):
  """ Get a blobstore url for uploading a file """
  draft_id = int(request.GET.get('id'))
  prefix = request.GET.get('type')
  path = '/%s/%d/add-file%s' % (prefix, draft_id, get_user_override(request))
  upload_url = blobstore.create_upload_url(path)
  return HttpResponse(upload_url)

# -----------------------------------------------------------------------------
#  Org home page tools
# -----------------------------------------------------------------------------

def _is_valid_rollover_target(source, target_cycle):
  return source.grant_cycle.get_type() == target_cycle.get_type()


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

# -----------------------------------------------------------------------------
#  View apps/files
# -----------------------------------------------------------------------------

def _view_permission(user, application):
  """ Return a number indicating viewing permission for a submitted app.

      Args:
        user: django user object
        application: GrantApplication

      Returns:
        0 - anon viewer or member without permission to view
        1 - member with permission to view
        2 - staff
        3 - app creator
  """
  if user.is_staff:
    return 2
  elif user == getattr(application.organization, 'user', None):
    return 3
  else:
    try:
      member = Member.objects.select_related().get(user=user)
      for ship in member.membership_set.all():
        if ship.giving_project in application.giving_projects.all():
          return 1
      return 0
    except Member.DoesNotExist:
      return 0

def view_application(request, app_id):
  app = get_object_or_404(models.GrantApplication, pk=app_id)
  answers = (models.NarrativeAnswer.objects
      .filter(grant_application=app)
      .select_related('cycle_narrative__narrative_question')
      .order_by('cycle_narrative__order'))

  if not request.user.is_authenticated():
    perm = 0
  else:
    perm = _view_permission(request.user, app)
  logger.info('perm is ' + str(perm))

  form = get_form_for_cycle(app.grant_cycle)(app.grant_cycle)

  form_only = request.GET.get('form')
  if form_only:
    return render(request, 'grants/reading.html',
                  {'app': app, 'form': form, 'perm': perm})
  file_urls = get_file_urls(request, app)
  print_urls = get_file_urls(request, app, printing=True)
  awards = {}
  for papp in app.projectapp_set.all():
    if hasattr(papp, 'givingprojectgrant'):# and hasattr(papp.givingprojectgrant, 'yearendreport'):
      awards[papp.giving_project] = papp.givingprojectgrant

  return render(request, 'grants/reading_sidebar.html', {
    'app': app, 'answers': answers, 'form': form, 'file_urls': file_urls,
    'print_urls': print_urls, 'awards': awards, 'perm': perm
  })

def view_blob(request, blobkey):
  blobinfo = blobstore.BlobInfo.get(blobkey)
  if blobinfo:
    return HttpResponse(blobstore.BlobReader(blobinfo).read(),
                       content_type=blobinfo.content_type)
  else:
    raise Http404


def serve_app_file(application, field_name):
  """ Returns response containing file from the Blobstore

    Arguments:
      application: GrantApplication or DraftGrantApplication
      field_name: name of the file field
  """

  file_field = getattr(application, field_name)
  if not file_field:
    logger.warning('Draft/app does not have a %s', field_name)
    raise Http404

  blobinfo = find_blobinfo(file_field)

  return HttpResponse(blobstore.BlobReader(blobinfo).read(),
                       content_type=blobinfo.content_type)

def view_file(request, obj_type, obj_id, field_name):
  model_types = {
    'app': models.GrantApplication,
    'report': models.YearEndReport,
    'adraft': models.DraftGrantApplication,
    'rdraft': models.YERDraft
  }
  if obj_type not in model_types:
    logger.warning('Unknown obj type %s', obj_type)
    raise Http404

  obj = get_object_or_404(model_types[obj_type], pk=obj_id)
  return serve_app_file(obj, field_name)

def view_yer(request, report_id):

  report = get_object_or_404(models.YearEndReport.objects.select_related(), pk=report_id)

  award = report.award
  projectapp = award.projectapp
  if not request.user.is_authenticated():
    perm = 0
  else:
    perm = _view_permission(request.user, projectapp.application)

  if not report.visible and perm < 2:
    return render(request, 'grants/blocked.html', {})

  form = YearEndReportForm(instance=report)

  file_urls = get_file_urls(request, report, printing=False)

  return render(request, 'grants/yer_display.html', {
    'report': report, 'form': form, 'award': award, 'projectapp': projectapp,
    'file_urls': file_urls, 'perm': perm})

# -----------------------------------------------------------------------------
#  Admin tools
# -----------------------------------------------------------------------------

def revert_app_to_draft(request, app_id):
  """ Turn a submitted application back into a draft by creating a
    DraftGrantApplication with all of its content and then deleting the
    GrantApplication.
  """

  submitted_app = get_object_or_404(models.GrantApplication, pk=app_id)

  if request.method == 'POST':
    draft = models.DraftGrantApplication.objects.create_from_submitted_app(submitted_app)
    models.GrantApplicationLog.objects.filter(application_id=app_id).update(application_id=None)
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

# -----------------------------------------------------------------------------
#  Reporting
# -----------------------------------------------------------------------------

def grants_report(request):
  """ Handles grant reporting

    Displays all reporting forms
    Uses report-type-specific methods to handle POSTs
  """

  app_form = AppReportForm()
  org_form = OrgReportForm()
  gp_grant_form = GPGrantReportForm()
  sponsored_form = SponsoredAwardReportForm()

  context = {
    'app_form': app_form,
    'org_form': org_form,
    'gp_grant_form': gp_grant_form,
    'sponsored_form': sponsored_form
  }

  if request.method == 'POST':
    # Determine type of report
    if 'run-application' in request.POST:
      logger.info('App report')
      form = AppReportForm(request.POST)
      context['app_form'] = form
      context['active_form'] = '#application-form'
      results_func = get_app_results

    elif 'run-organization' in request.POST:
      logger.info('Org report')
      form = OrgReportForm(request.POST)
      context['org_form'] = form
      context['active_form'] = '#organization-form'
      results_func = get_org_results

    elif 'run-giving-project-grant' in request.POST:
      logger.info('Giving project grant report')
      form = GPGrantReportForm(request.POST)
      context['award_form'] = form
      context['active_form'] = '#giving-project-grant-form'
      results_func = get_gpg_results

    elif 'run-sponsored-award' in request.POST:
      logger.info('Sponsored award report')
      form = SponsoredAwardReportForm(request.POST)
      context['award_form'] = form
      context['active_form'] = '#sponsored-award-form'
      results_func = get_sponsored_award_results

    else:
      logger.error('Unknown report type')
      form = None

    if form and form.is_valid():
      options = form.cleaned_data
      logger.info('A valid form: ' + str(options))

      # get results
      field_names, results = results_func(options)

      # format results
      if options['format'] == 'browse':
        return render_to_response('grants/report_results.html',
                                  {'results': results, 'field_names': field_names})
      elif options['format'] == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % 'grantapplications'
        writer = unicodecsv.writer(response)
        writer.writerow(field_names)
        for row in results:
          writer.writerow(row)
        return response
    else:
      logger.warning('Invalid form!')

  # human-friendly lists of always-included fields
  context['app_base'] = 'submission time, organization name, grant cycle'
  context['gpg_base'] = ('date check was mailed, amount (total and by year), '
                         'organization, giving project, grant cycle')
  context['sponsored_base'] = 'date check was mailed, amount, organization'
  context['org_base'] = 'name'
  return render(request, 'grants/reporting.html', context)

def get_min_max_year(options):
  current_tz = timezone.get_current_timezone()
  min_year = datetime.strptime(options['year_min'], '%Y') # will default to beginning of year
  min_year = timezone.make_aware(min_year, current_tz)
  max_year = datetime.strptime(options['year_max'] + '-12-31 23:59:59', '%Y-%m-%d %H:%M:%S')
  max_year = timezone.make_aware(max_year, current_tz)
  return min_year, max_year

def get_app_results(options):
  """ Fetches application report results

  Arguments:
    options - cleaned_data from a request.POST-filled instance of AppReportForm

  Returns:
    A list of display-formatted field names. Example:
      ['Submitted', 'Organization', 'Grant cycle']

    A list of applications & related info. Example:
      [
        ['2011-04-20 06:18:36+0:00', 'Justice League', 'LGBTQ Grant Cycle'],
        ['2013-10-23 09:08:56+0:00', 'ACLU of Idaho', 'General Grant Cycle'],
      ]
  """
  logger.info('Get app results')

  apps = models.GrantApplication.objects.order_by('-submission_time').select_related(
      'organization', 'grant_cycle')

  # filters
  min_year, max_year = get_min_max_year(options)
  apps = apps.filter(submission_time__gte=min_year, submission_time__lte=max_year)

  if options.get('organization_name'):
    apps = apps.filter(organization__name__contains=options['organization_name'])
  if options.get('city'):
    apps = apps.filter(city=options['city'])
  if options.get('state'):
    apps = apps.filter(state__in=options['state'])
  if options.get('has_fiscal_sponsor'):
    apps = apps.exclude(fiscal_org='')

  if options.get('pre_screening_status'):
    apps = apps.filter(pre_screening_status__in=options.get('pre_screening_status'))
  if options.get('screening_status'):
    apps = apps.filter(projectapp__screening_status__in=options.get('screening_status'))
  if options.get('poc_bonus'):
    apps = apps.filter(scoring_bonus_poc=True)
  if options.get('geo_bonus'):
    apps = apps.filter(scoring_bonus_geo=True)
  if options.get('grant_cycle'):
    apps = apps.filter(grant_cycle__title__in=options.get('grant_cycle'))
  if options.get('giving_projects'):
    apps = apps.prefetch_related('giving_projects')
    apps = apps.filter(giving_projects__title__in=options.get('giving_projects'))

  # fields
  fields = (['submission_time', 'organization', 'grant_cycle'] +
            options['report_basics'] + options['report_contact'] +
            options['report_org'] + options['report_proposal'] +
            options['report_budget'])
  if options['report_fiscal']:
    fields += models.GrantApplication.fields_starting_with('fiscal')
    fields.remove('fiscal_letter')
  # TODO re-implement references reporting
  if options['report_bonuses']:
    fields.append('scoring_bonus_poc')
    fields.append('scoring_bonus_geo')

  # format headers
  field_names = [f.capitalize().replace('_', ' ') for f in fields]

  # gp screening, grant awards
  get_gps = False
  get_gp_ss = False
  get_awards = False
  if options['report_gps']:
    field_names.append('Assigned GPs')
    get_gps = True
  if options['report_gp_screening']:
    field_names.append('GP screening status')
    get_gp_ss = True
  if options['report_award']:
    field_names.append('Awarded')
    get_awards = True

  # execute queryset, populate results
  results = []
  for app in apps:
    row = []

    # application fields
    for field in fields:
      if field == 'pre_screening_status':
        # convert screening status to human-readable version
        val = getattr(app, field)
        if val:
          convert = dict(gc.PRE_SCREENING)
          val = convert[val]
        row.append(val)
      elif field == 'submission_time':
        row.append(local_date_str(getattr(app, field)))
      else:
        row.append(getattr(app, field))

    # gp GPs, screening status, awards
    if get_gps or get_awards or get_gp_ss:
      award_col = ''
      ss_col = ''
      gp_col = ''
      papps = app.projectapp_set.all()
      if papps:
        for papp in papps:
          if get_gps:
            if gp_col != '':
              gp_col += ', '
            gp_col += '%s' % papp.giving_project.title
          if get_awards:
            try:
              award = papp.givingprojectgrant
              if award_col != '':
                award_col += ', '
              award_col += '%s %s ' % (award.total_amount(), papp.giving_project.title)
            except models.GivingProjectGrant.DoesNotExist:
              pass
          if get_gp_ss:
            if ss_col != '':
              ss_col += ', '
            if papp.screening_status:
              ss_col += '%s (%s) ' % (dict(gc.SCREENING)[papp.screening_status],
                papp.giving_project.title)
            else:
              ss_col += '%s (none) ' % papp.giving_project.title
      if get_gps:
        row.append(gp_col)
      if get_gp_ss:
        row.append(ss_col)
      if get_awards:
        row.append(award_col)

    results.append(row)

  return field_names, results

def get_org_results(options):
  """ Fetch organization report results

  Args:
    options: cleaned_data from a request.POST-filled instance of OrgReportForm

  Returns:
    A list of display-formatted field names. Example:
      ['Name', 'Login', 'State']

    A list of organization & related info. Each item is a list of requested values
    Example: [
        ['Fancy pants org', 'fancy@pants.org', 'ID'],
        ['Justice League', 'trouble@gender.org', 'WA']
      ]
  """

  # initial queryset
  orgs = models.Organization.objects.all()

  # filters
  reg = options.get('registered')
  if reg is True:
    orgs = orgs.exclude(user__isnull=True)
  elif reg is False:
    org = orgs.filter(user__isnull=True)
  if options.get('organization_name'):
    orgs = orgs.filter(name__contains=options['organization_name'])
  if options.get('city'):
    orgs = orgs.filter(city=options['city'])
  if options.get('state'):
    orgs = orgs.filter(state__in=options['state'])
  if options.get('has_fiscal_sponsor'):
    orgs = orgs.exclude(fiscal_org='')

  # fields
  fields = ['name']
  if options.get('report_account_email'):
    fields.append('email')
  fields += options['report_contact'] + options['report_org']
  if options.get('report_fiscal'):
    fields += models.GrantApplication.fields_starting_with('fiscal')
    fields.remove('fiscal_letter')

  field_names = [f.capitalize().replace('_', ' ') for f in fields] # for display

  # related objects
  get_apps = False
  get_awards = False
  if options.get('report_applications'):
    get_apps = True
    orgs = orgs.prefetch_related('grantapplication_set')
    field_names.append('Grant applications')
  if options.get('report_awards'):
    orgs = orgs.prefetch_related('grantapplication_set')
    orgs = orgs.prefetch_related('sponsoredprogramgrant_set')
    field_names.append('Grants awarded')
    get_awards = True

  # execute queryset, build results
  results = []
  linebreak = '\n' if options['format'] == 'csv' else '<br>'
  for org in orgs:
    row = []

    # org fields
    for field in fields:
      if field == 'email':
        row.append(org.get_email())
      else:
        row.append(getattr(org, field))

    awards_str = ''
    if get_apps or get_awards:
      apps_str = ''

      for app in org.grantapplication_set.all():
        if get_apps:
          apps_str += (app.grant_cycle.title + ' ' +
            app.submission_time.strftime('%m/%d/%Y') + linebreak)

        # giving project grants
        if get_awards:
          for papp in app.projectapp_set.all():
            try:
              award = papp.givingprojectgrant
              timestamp = award.check_mailed or award.created
              if timestamp:
                timestamp = timestamp.strftime('%m/%d/%Y')
              else:
                timestamp = 'No timestamp'
              awards_str += u'${} {} {}{}'.format(award.total_amount(),
                award.projectapp.giving_project.title, timestamp, linebreak)
            except models.GivingProjectGrant.DoesNotExist:
              pass

      if get_apps:
        row.append(apps_str)

    # sponsored program grants
    if get_awards:
      for award in org.sponsoredprogramgrant_set.all():
        awards_str += '$%s %s %s' % (award.amount, ' sponsored program grant ',
            (award.check_mailed or award.entered).strftime('%m/%d/%Y'))
        awards_str += linebreak
      row.append(awards_str)

    results.append(row)

  return field_names, results

def get_gpg_results(options):
  """ Fetch giving project grant report results

  Args:
    options: cleaned_data from a request.POST-filled instance of AwardReportForm

  Returns:
    field_names: A list of display-formatted field names.
      Example: ['Amount', 'Check mailed', 'Organization']

    results: A list of requested values for each award.
      Example (matching field_names example): [
          ['10000', '2013-10-23 09:08:56+0:00', 'Fancy pants org'],
          ['5987', '2011-08-04 09:08:56+0:00', 'Justice League']
        ]
  """

  # initial queryset
  gp_awards = models.GivingProjectGrant.objects.select_related(
      'projectapp__application__organization', 'projectapp__giving_project')

  # filters
  min_year, max_year = get_min_max_year(options)
  gp_awards = gp_awards.filter(created__gte=min_year, created__lte=max_year)

  if options.get('organization_name'):
    gp_awards = gp_awards.filter(
        projectapp__application__organization__name__contains=options['organization_name'])

  if options.get('city'):
    gp_awards = gp_awards.filter(projectapp__application__city=options['city'])

  if options.get('state'):
    gp_awards = gp_awards.filter(projectapp__application__state__in=options['state'])

  if options.get('has_fiscal_sponsor'):
    gp_awards = gp_awards.exclude(projectapp__application__fiscal_org='')

  if options.get('grant_cycle'):
    gp_awards = gp_awards.filter(
      projectapp__application__grant_cycle__title__in=options.get('grant_cycle')
    )
  if options.get('giving_projects'):
    gp_awards = gp_awards.filter(
      projectapp__giving_project__title__in=options.get('giving_projects')
    )

  # fields
  fields = ['check_mailed', 'first_year_amount', 'second_year_amount', 'total_amount',
            'organization', 'giving_project', 'grant_cycle']

  if options.get('report_id'):
    fields.append('id')
  if options.get('report_check_number'):
    fields.append('check_number')
  if options.get('report_date_approved'):
    fields.append('approved')
  if options.get('report_agreement_dates'):
    fields.append('agreement_mailed')
    fields.append('agreement_returned')
  if options.get('report_year_end_report_due'):
    fields.append('year_end_report_due')
  if options.get('report_support_type'):
    fields.append('support_type')

  org_fields = options['report_contact'] + options['report_org']
  if options.get('report_fiscal'):
    org_fields += models.GrantApplication.fields_starting_with('fiscal')
    org_fields.remove('fiscal_letter')

  # get values
  results = []
  for award in gp_awards:
    row = []
    for field in fields:
      if field == 'organization':
        row.append(award.projectapp.application.organization.name)
      elif field == 'grant_cycle':
        row.append(award.projectapp.application.grant_cycle.title)
      elif field == 'support_type':
        row.append(award.projectapp.application.support_type)
      elif field == 'giving_project':
        row.append(award.projectapp.giving_project.title)
      elif field == 'year_end_report_due':
        row.append(award.next_yer_due())
      elif field == 'first_year_amount':
        row.append(award.amount)
      elif field == 'second_year_amount':
        row.append(award.second_amount or '')
      elif field == 'total_amount':
        row.append(award.total_amount())
      else:
        row.append(getattr(award, field, ''))
    for field in org_fields:
      row.append(getattr(award.projectapp.application.organization, field))
    results.append(row)

  field_names = [f.capitalize().replace('_', ' ') for f in fields]
  field_names += ['Org. ' + f.capitalize().replace('_', ' ') for f in org_fields]

  return field_names, results

def get_sponsored_award_results(options):
  sponsored = models.SponsoredProgramGrant.objects.select_related('organization')

  min_year, max_year = get_min_max_year(options)
  sponsored = sponsored.filter(entered__gte=min_year, entered__lte=max_year)

  if options.get('organization_name'):
    sponsored = sponsored.filter(organization__name__contains=options['organization_name'])
  if options.get('city'):
    sponsored = sponsored.filter(organization__city=options['city'])
  if options.get('state'):
    sponsored = sponsored.filter(organization__state__in=options['state'])
  if options.get('has_fiscal_sponsor'):
    sponsored = sponsored.exclude(organization__fiscal_org='')

  # fields
  fields = ['check_mailed', 'amount', 'organization']
  if options.get('report_id'):
    fields.append('id')
  if options.get('report_check_number'):
    fields.append('check_number')
  if options.get('report_date_approved'):
    fields.append('approved')

  org_fields = options['report_contact'] + options['report_org']
  if options.get('report_fiscal'):
    org_fields += models.GrantApplication.fields_starting_with('fiscal')
    org_fields.remove('fiscal_letter')

  # get values
  results = []
  for award in sponsored:
    row = []
    for field in fields:
      if hasattr(award, field):
        row.append(getattr(award, field))
      else:
        row.append('')
    for field in org_fields:
      row.append(getattr(award.organization, field))
    results.append(row)

  field_names = [f.capitalize().replace('_', ' ') for f in fields]
  field_names += ['Org. ' + f.capitalize().replace('_', ' ') for f in org_fields]

  return field_names, results

# -----------------------------------------------------------------------------
#  Helpers
# -----------------------------------------------------------------------------

def get_file_urls(request, app, printing=False):
  """ Get html links to view files in a given app or year-end report, draft or final

    Takes into account whether it can be viewed in google doc viewer

    Args:
      request: HttpRequest
      app: one of GrantApplication, DraftGrantApplication, YearEndReport, YERDraft
      printing: if True, will not use doc viewer for excel files to avoid known printing bug

    Returns:
      file_urls: a dict of urls for viewing each file
        key is name of django model field e.g. budget, budget1, funding_sources
        value is string of html for linking to the uploaded file
      returns an empty dict if the given object is not valid
  """
  app_urls = {
    'funding_sources': '',
    'demographics': '',
    'fiscal_letter': '',
    'budget1': '',
    'budget2': '',
    'budget3': '',
    'project_budget_file': ''
  }
  report_urls = {
    'photo1': '',
    'photo2': '',
    'photo3': '',
    'photo4': '',
    'photo_release': ''
  }
  base_url = request.build_absolute_uri('/')

  # determine type of app and set base url and starting dict accordingly
  if isinstance(app, models.GrantApplication):
    base_url += 'grants/app-file/'
    file_urls = app_urls
    file_urls['budget'] = ''
  elif isinstance(app, models.DraftGrantApplication):
    file_urls = app_urls
    base_url += 'grants/adraft-file/'
  elif isinstance(app, models.YearEndReport):
    file_urls = report_urls
    base_url += 'grants/report-file/'
  elif isinstance(app, models.YERDraft):
    file_urls = report_urls
    base_url += 'grants/rdraft-file/'
  else:
    logger.error('get_file_urls received invalid object')
    return {}

  # check file fields, compile links
  for field in file_urls:
    value = getattr(app, field)
    if value:
      ext = value.name.lower().split('.')[-1]
      file_urls[field] += base_url + str(app.pk) + u'-' + field
      if not settings.DEBUG and ext in gc.VIEWER_FILE_TYPES:
        if printing:
          if not (ext == 'xls' or ext == 'xlsx'):
            file_urls[field] = 'https://docs.google.com/viewer?url=' + file_urls[field]
        else:
          file_urls[field] = ('https://docs.google.com/viewer?url=' +
                              file_urls[field] + '&embedded=true')
  return file_urls
