import datetime
import json
import logging
import urllib2

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.http import HttpResponse, Http404
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from google.appengine.ext import blobstore, deferred

from libs import unicodecsv

from sjfnw import constants
from sjfnw.fund.models import Member
from sjfnw.grants.decorators import registered_org
from sjfnw.grants.forms import (AdminRolloverForm, LoginAsOrgForm, LoginForm,
   AppReportForm, AwardReportForm, OrgReportForm, RegisterForm,
   RolloverForm, RolloverYERForm)
from sjfnw.grants.modelforms import (GrantApplicationModelForm, OrgProfile,
    YearEndReportForm)
from sjfnw.grants.utils import local_date_str, ServeBlob, DeleteBlob
from sjfnw.grants import models

logger = logging.getLogger('sjfnw')

# CONSTANTS

LOGIN_URL = '/apply/login/'

# PUBLIC ORG VIEWS

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

  if request.method == 'POST':
    register = RegisterForm(request.POST)

    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']
      org = request.POST['organization']

      #create User
      created = User.objects.create_user(username_email, username_email, password)
      created.first_name = org
      created.last_name = '(organization)'

      # create or update org
      try: # if matching org with no email exists
        org = models.Organization.objects.get(name=org)
        org.email = username_email
        logger.info('matching org name found. setting email')
        org.save()
        created.is_active = False
      except models.Organization.DoesNotExist: # if not, create new
        logger.info('Creating new org')
        new_org = models.Organization(name=org, email=username_email)
        new_org.save()
      created.save()

      #try to log in
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

  else: #GET
    register = RegisterForm()
  form = LoginForm()

  return render(request, 'grants/org_login_register.html', {
    'form': form, 'register': register
  })

def org_support(request):
  return render(request, 'grants/org_support.html', {
    'support_email': constants.SUPPORT_EMAIL,
    'support_form': constants.GRANT_SUPPORT_FORM
  })

def cycle_info(request, cycle_id):
  """ Fetches cycle info page from external URL and embeds it """
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  error_display = ('<h4 class="center">Sorry, the cycle information page could '
      'not be loaded.<br>Try visiting it directly: <a href="' +
      cycle.info_page +'" target="_blank">grant cycle information</a>')
  content = ''
  if not cycle.info_page:
    raise Http404
  try:
    info_page = urllib2.urlopen(cycle.info_page)
  except urllib2.HTTPError as err:
    logger.error('Error fetching cycle info page; HTTPError: %s %s', err.code, err.reason)
  except urllib2.URLError as err:
    logger.error('Error fetching cycle info page; URLError: ' + str(err.reason))
  except IOError as err:
    logger.error('Unknown error fetching cycle info page: %s', err)
  else:
    content = info_page.read()
    start = content.find('<div id="content"')
    end = content.find('<!-- /#content')
    content = content[start:end].replace('modules/file/icons', 'static/images')
    if content == '':
      logger.error('Info page content at %s could not be split', cycle.info_page)
    else:
      logger.info('Received info page content from ' + cycle.info_page)
  finally:
    return render(request, 'grants/cycle_info.html', {
      'cycle': cycle, 'content': content or error_display
    })

# REGISTERED ORG VIEWS

@login_required(login_url=LOGIN_URL)
@registered_org()
def org_home(request, organization):

  saved = (models.DraftGrantApplication.objects.filter(organization=organization)
                                               .select_related('grant_cycle'))
  submitted = (models.GrantApplication.objects.filter(organization=organization)
                                              .select_related('giving_projects')
                                              .order_by('-submission_time'))
  cycles = (models.GrantCycle.objects
      .exclude(private=True)
      .filter(close__gt=timezone.now()-datetime.timedelta(days=180))
      .order_by('open'))
  submitted_cycles = submitted.values_list('grant_cycle', flat=True)
  yer_drafts = (models.YERDraft.objects
      .filter(award__projectapp__application__organization_id=organization.pk)
      .select_related())

  closed, current, applied, upcoming = [], [], [], []
  for cycle in cycles:
    status = cycle.get_status()
    if status == 'open':
      if cycle.pk in submitted_cycles:
        applied.append(cycle)
      else:
        current.append(cycle)
    elif status == 'closed':
      closed.append(cycle)
    elif status == 'upcoming':
      upcoming.append(cycle)

  # staff override
  user_override = request.GET.get('user')
  if user_override:
    user_override = '?user=' + user_override

  return render(request, 'grants/org_home.html', {
    'organization': organization,
    'submitted': submitted,
    'saved': saved,
    'cycles': cycles,
    'closed': closed,
    'open': current,
    'upcoming': upcoming,
    'applied': applied,
    'ydrafts': yer_drafts,
    'user_override': user_override
  })

@login_required(login_url=LOGIN_URL)
@registered_org()
def grant_application(request, organization, cycle_id):
  """ Get or submit the whole application form """

  # staff override
  user_override = request.GET.get('user')
  if user_override:
    user_override = '?user=' + user_override

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)

  # check for app already submitted
  if models.GrantApplication.objects.filter(organization=organization, grant_cycle=cycle):
    return render(request, 'grants/already_applied.html', {
      'organization': organization, 'cycle': cycle
    })

  draft, created = models.DraftGrantApplication.objects.get_or_create(
      organization=organization, grant_cycle=cycle)
  profiled = False

  #TODO TEMP HACK
  recently_edited = False

  if request.method == 'POST':
    if not draft.editable():
      return render(request, 'grants/submitted_closed.html', {'cycle': cycle})

    #get fields & files from draft
    draft_data = json.loads(draft.contents)
    files_data = model_to_dict(draft, fields=draft.file_fields())

    #add automated fields
    draft_data['organization'] = organization.pk
    draft_data['grant_cycle'] = cycle.pk

    form = GrantApplicationModelForm(cycle, draft_data, files_data)

    if form.is_valid():
      logger.info('========= Application form valid')

      form.save()

      subject = 'Grant application submitted'
      from_email = constants.GRANT_EMAIL
      to_email = organization.email
      html_content = render_to_string('grants/email_submitted.html', {
        'org': organization, 'cycle': cycle
      })
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email,
          [to_email], [constants.SUPPORT_EMAIL])
      msg.attach_alternative(html_content, 'text/html')
      msg.send()
      logger.info('Application created; confirmation email sent to ' + to_email)

      draft.delete()

      return redirect('/apply/submitted')

    else: #INVALID SUBMISSION
      logger.info('Application form invalid')
      logger.info(form.errors)

  else: # GET

    # check for recent autosave - may indicate multiple editors
    recently_edited = draft.modified + datetime.timedelta(seconds=35) > timezone.now()

    if created or draft.contents == '{}':
      # new/blank draft; load profile
      org_dict = model_to_dict(organization, exclude=['fiscal_letter'])
      draft.fiscal_letter = organization.fiscal_letter
      draft.contents = json.dumps(org_dict)
      draft.save()
      logger.debug('Created new draft')
      if cycle.info_page: # redirect to instructions first
        return render(request, 'grants/cycle_info.html', {'cycle': cycle})

    else: # load the draft
      org_dict = json.loads(draft.contents)
      timeline = []
      for i in range(15): # covering both timeline formats
        if 'timeline_' + str(i) in org_dict:
          timeline.append(org_dict['timeline_' + str(i)])
      org_dict['timeline'] = json.dumps(timeline)
      logger.debug('Loaded draft')

    # check if draft can be submitted
    if not draft.editable():
      return render(request, 'grants/closed.html', {'cycle': cycle})

    # try to determine initial load - hacky way
    # 1) if referer, make sure it wasn't from copy
    # 2) check for mission from profile
    # 3) make sure grant request is not there (since it's not in profile)
    referer = request.META.get('HTTP_REFERER')
    if (not (referer and referer.find('copy') != -1) and
        organization.mission and
        ((not 'grant_request' in org_dict) or (not org_dict['grant_request']))):
      profiled = True

    #create form
    form = GrantApplicationModelForm(cycle, initial=org_dict)

  #get draft files
  file_urls = GetFileURLs(request, draft)
  #TODO test this replacement
  #link_template = ('<a href="{0}" target="_blank" title="">{1}</a>{1}'
  #                '[<a onclick="fileUploads.removeFile(\'{2}\');">remove</a>]')
  #file_urls[field] = link_template.format(url, name, field)
  for field, url in file_urls.iteritems():
    if url:
      name = getattr(draft, field).name.split('/')[-1]
      file_urls[field] = ('<a href="' + url + '" target="_blank" title="' +
          name + '">' + name + '</a> [<a onclick="fileUploads.removeFile(\'' +
          field + '\');">remove</a>]')
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  return render(request, 'grants/org_app.html', {
      'form': form, 'cycle': cycle, 'file_urls': file_urls,
      'limits': models.GrantApplication.NARRATIVE_CHAR_LIMITS,
      'draft': draft, 'profiled': profiled, 'org': organization,
      'user_override': user_override, 'flag': recently_edited
  })

def autosave_app(request, cycle_id):
  """ Save non-file fields to a draft """

  # don't return actual redirect since this is an ajax request
  if not request.user.is_authenticated():
    return HttpResponse(LOGIN_URL, status=401)

  username = request.user.username

  # check for staff impersonating an org - override username
  if request.user.is_staff and request.GET.get('user'):
    username = request.GET.get('user')
    logger.info('Staff override - %s logging in as %s', request.user.username, username)

  try:
    organization = models.Organization.objects.get(email=username)
    logger.info(organization)
  except models.Organization.DoesNotExist:
    return HttpResponse('/apply/nr', status=401)

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  draft = get_object_or_404(models.DraftGrantApplication,
      organization=organization, grant_cycle=cycle)

  if request.method == 'POST':
    curr_user = request.POST.get('user_id')

    #check for simultaneous editing
    #TODO call this force to distinguish from staff override
    if request.GET.get('override') != 'true':
      # check if edited recently TODO reusable method
      if draft.modified + datetime.timedelta(seconds=35) > timezone.now():
        if draft.modified_by and draft.modified_by != curr_user: # last save wasn't this userid
          logger.info('Requiring confirmation')
          return HttpResponse('confirm override', status=409)
    else:
      logger.info('Override skipped check')

    logger.debug('Autosaving')
    draft.contents = json.dumps(request.POST)
    draft.modified = timezone.now()
    draft.modified_by = curr_user
    draft.save()
    return HttpResponse('success')

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
    return Http404

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
    return HttpResponse('ERROR') #TODO use status code

  file_urls = GetFileURLs(request, draft)
  # TODO test this replacement:
  #content = (u'{0} ~~<a href="{1}" target="_blank" title="{2}">{2}</a> '
  #    '[<a onclick="fileUploads.removeFile(\'{0}\');">remove</a>]').format(
  #        field_name, file_urls[field_name], blob_file)
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
  draft = get_object_or_404(models.DraftGrantApplication, pk=draft_id)

  if hasattr(draft, file_field):
    old = getattr(draft, file_field)
    deferred.defer(DeleteBlob, old)
    setattr(draft, file_field, '')
    draft.modified = timezone.now()
    draft.save()
  else:
    logger.error('Tried to remove non-existent field: ' + file_field)
  return HttpResponse('success')


def RefreshUploadUrl(request):
  """ Get a blobstore url for uploading a file """

  # staff override
  user_override = request.GET.get('user')
  if user_override:
    user_override = '?user=' + user_override
  else:
    user_override = ''

  draft_id = int(request.GET.get('id'))
  prefix = request.GET.get('type')

  upload_url = blobstore.create_upload_url('/%s/%d/add-file' % (prefix, draft_id) + user_override)
  return HttpResponse(upload_url)


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

  #staff override
  user_override = request.GET.get('user')
  if user_override:
    user_override = '?user=' + user_override

  # get award, make sure org matches
  award = get_object_or_404(models.GivingProjectGrant, pk=award_id)
  app = award.projectapp.application
  if app.organization_id != organization.pk:
    logger.warning('Trying to edit someone else\'s YER')
    return redirect(org_home)

  # check if already submitted
  if models.YearEndReport.objects.filter(award=award):
    logger.warning('YER already exists')
    return redirect(org_home)

  # get or create draft
  draft, created = models.YERDraft.objects.get_or_create(award=award)

  if request.method == 'POST':
    draft_data = json.loads(draft.contents)
    files_data = model_to_dict(draft, fields=['photo1', 'photo2', 'photo3',
                                              'photo4', 'photo_release'])
    logger.info(files_data)
    draft_data['award'] = award.pk
    form = YearEndReportForm(draft_data, files_data)
    if form.is_valid():
      logger.info('Valid YER')
      # save YER and delete draft
      yer = form.save()
      draft.delete()

      # send confirmation email
      html_content = render_to_string('grants/email_yer_submitted.html')
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives('Year-end report submitted', #subject
                                    text_content,
                                    constants.GRANT_EMAIL, #from
                                    [yer.email], #to
                                    [constants.SUPPORT_EMAIL]) #bcc
      msg.attach_alternative(html_content, 'text/html')
      msg.send()
      logger.info('YER submission confirmation email send to %s', yer.email)
      return redirect('/report/submitted')

    else:
      logger.info(form.errors)

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

  file_urls = GetFileURLs(request, draft)
  for field, url in file_urls.iteritems():
    if url:
      name = getattr(draft, field).name.split('/')[-1]
      file_urls[field] = ('<a href="' + url + '" target="_blank" title="' +
          name + '">' + name + '</a> [<a onclick="fileUploads.removeFile(\'' +
          field + '\');">remove</a>]')
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  return render(request, 'grants/yer_form.html', {
      'form': form, 'org': organization, 'draft': draft, 'award': award,
      'file_urls': file_urls, 'user_override': user_override
  })


# ORG COPY DELETE APPS
@login_required(login_url=LOGIN_URL)
@registered_org()
def CopyApp(request, organization):

  user_override = '?user=' + request.GET.get('user') if request.GET.get('user') else ''

  if request.method == 'POST':
    form = RolloverForm(organization, request.POST)
    if form.is_valid():
      new_cycle = form.cleaned_data.get('cycle')
      draft = form.cleaned_data.get('draft')
      app = form.cleaned_data.get('application')

      #get cycle
      try:
        cycle = models.GrantCycle.objects.get(pk=int(new_cycle))
      except models.GrantCycle.DoesNotExist:
        logger.error('CopyApp GrantCycle ' + new_cycle + ' not found')
        return render(request, 'grants/copy_app_error.html')

      #make sure the combo does not exist already
      new_draft, created = models.DraftGrantApplication.objects.get_or_create(
          organization=organization, grant_cycle=cycle)
      if not created:
        logger.error('CopyApp the combo already exists!?')
        return render(request, 'grants/copy_app_error.html')

      #get app/draft and its contents (json format for draft)
      if app:
        try:
          application = models.GrantApplication.objects.get(pk=int(app))
          content = model_to_dict(application,
                                  exclude=application.file_fields() + [
                                    'organization', 'grant_cycle',
                                    'submission_time', 'pre_screening_status',
                                    'giving_projects', 'scoring_bonus_poc',
                                    'scoring_bonus_geo', 'cycle_question',
                                    'timeline', 'budget' #old all-in-one budget
                                  ])
          content.update(dict(zip(
              ['timeline_' + str(i) for i in range(15)],
              json.loads(application.timeline)
              )))
          content = json.dumps(content)
        except models.GrantApplication.DoesNotExist:
          logger.error('CopyApp - submitted app ' + app + ' not found')
      elif draft:
        try:
          application = models.DraftGrantApplication.objects.get(pk=int(draft))
          content = json.loads(application.contents)
          logger.info(content)
          content['cycle_question'] = ''
          logger.info(content)
          content = json.dumps(content)
        except models.DraftGrantApplication.DoesNotExist:
          logger.error('CopyApp - draft ' + app + ' not found')
      else:
        logger.error('CopyApp no draft or app...')
        return render(request, 'grants/copy_app_error.html')

      #set contents & files
      new_draft.contents = content
      for field in application.file_fields():
        setattr(new_draft, field, getattr(application, field))
      new_draft.save()
      logger.info('CopyApp -- content and files set')

      return redirect('/apply/' + new_cycle + user_override)

    else: #INVALID FORM
      logger.warning('form invalid')
      logger.info(form.errors)
      #TODO
      cycle_count = str(form['cycle']).count('<option value') - 1
      apps_count = (str(form['application']).count('<option value') +
                    str(form['draft']).count('<option value') - 2)

  else: #GET
    form = RolloverForm(organization)
    cycle_count = str(form['cycle']).count('<option value') - 1
    apps_count = (str(form['application']).count('<option value') +
                  str(form['draft']).count('<option value') -2)
    logger.info(cycle_count)
    logger.info(apps_count)

  return render(request, 'grants/org_app_copy.html',
                {'form': form, 'cycle_count': cycle_count, 'apps_count': apps_count})

@registered_org()
def DiscardDraft(request, organization, draft_id):

  #look for saved draft
  try:
    saved = models.DraftGrantApplication.objects.get(pk=draft_id)
    if saved.organization == organization:
      saved.delete()
      logger.info('Draft ' + str(draft_id) + ' discarded')
    else: #trying to delete another person's draft!?
      logger.warning('Failed attempt to discard draft ' + str(draft_id) +
                      ' by ' + unicode(organization))
    return redirect(org_home)
  except models.DraftGrantApplication.DoesNotExist:
    logger.error(str(request.user) + ' discard nonexistent draft')
    raise Http404


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
    exclude_awards = [r.award_id for r in reports] + [d.award_id for d in drafts]
    awards = (models.GivingProjectGrant.objects.select_related('award')
        .filter(projectapp__application__organization_id=organization.pk)
        .exclude(id__in=exclude_awards))
    if not awards:
      if exclude_awards:
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


# VIEW APPS/FILES

def view_permission(user, application):
  """ Return a number indicating viewing permission for a submitted app.

      Args:
        user: django user object
        application: GrantApplication

      Returns:
        0 - anon viewer
        1 - member with perm
        2 - staff
        3 - app creator
  """
  if user.is_staff:
    return 2
  elif user.email == application.organization.email:
    return 3
  else:
    try:
      member = Member.objects.select_related().get(email=user.email)
      for ship in member.membership_set.all():
        if ship.giving_project in application.giving_projects.all():
          return 1
      return 0
    except Member.DoesNotExist:
      return 0

def view_application(request, app_id):
  app = get_object_or_404(models.GrantApplication, pk=app_id)

  if not request.user.is_authenticated():
    perm = 0
  else:
    perm = view_permission(request.user, app)
  logger.info('perm is ' + str(perm))

  form = GrantApplicationModelForm(app.grant_cycle)

  form_only = request.GET.get('form')
  if form_only:
    return render(request, 'grants/reading.html',
                  {'app': app, 'form': form, 'perm': perm})
  file_urls = GetFileURLs(request, app)
  print_urls = GetFileURLs(request, app, printing=True)
  awards = {}
  for papp in app.projectapp_set.all():
    if hasattr(papp, 'givingprojectgrant'):# and hasattr(papp.givingprojectgrant, 'yearendreport'):
      awards[papp.giving_project] = papp.givingprojectgrant

  return render(request, 'grants/reading_sidebar.html',
                {'app': app, 'form': form, 'file_urls': file_urls, 'print_urls': print_urls,
                 'awards': awards, 'perm': perm})

def view_file(request, obj_type, obj_id, field_name):
  MODEL_TYPES = {
    'app': models.GrantApplication,
    'report': models.YearEndReport,
    'adraft': models.DraftGrantApplication,
    'rdraft': models.YERDraft
  }
  if not obj_type in MODEL_TYPES:
    logger.warning('Unknown obj type %s', obj_type)
    raise Http404

  obj = get_object_or_404(MODEL_TYPES[obj_type], pk=obj_id)
  return ServeBlob(obj, field_name)

def ViewDraftFile(request, draft_id, field_name):
  application = get_object_or_404(models.DraftGrantApplication, pk=draft_id)
  return ServeBlob(application, field_name)

def view_yer(request, report_id):
  logger.info('view_yer')

  report = get_object_or_404(models.YearEndReport.objects.select_related(), pk=report_id)

  award = report.award
  projectapp = award.projectapp
  if not request.user.is_authenticated():
    perm = 0
  else:
    perm = view_permission(request.user, projectapp.application)

  if not report.visible and perm < 2:
    return render(request, 'grants/blocked.html', {})

  form = YearEndReportForm(instance=report)

  file_urls = GetFileURLs(request, report, printing=False)

  return render(request, 'grants/yer_display.html', {
    'report': report, 'form': form, 'award': award, 'projectapp': projectapp,
    'file_urls': file_urls, 'perm': perm})


# ADMIN
def RedirToApply(request):
  return redirect('/apply/')

def AppToDraft(request, app_id):

  submitted_app = get_object_or_404(models.GrantApplication, pk=app_id)
  organization = submitted_app.organization
  grant_cycle = submitted_app.grant_cycle

  if request.method == 'POST':
    #create draft from app
    draft = models.DraftGrantApplication(organization=organization, grant_cycle=grant_cycle)
    content = model_to_dict(submitted_app,
                            exclude=submitted_app.file_fields() + [
                                'organization', 'grant_cycle',
                                'submission_time', 'pre_screening_status',
                                'giving_projects', 'scoring_bonus_poc',
                                'scoring_bonus_geo', 'timeline'])
    content.update(dict(zip(['timeline_' + str(i) for i in range(15)],
                            json.loads(submitted_app.timeline))
                       ))
    draft.contents = json.dumps(content)
    for field in submitted_app.file_fields():
      if hasattr(draft, field):
        setattr(draft, field, getattr(submitted_app, field))
    draft.modified = timezone.now()
    draft.save()
    logger.info('Reverted to draft, draft id ' + str(draft.pk))
    #delete app
    submitted_app.delete()
    #redirect to draft page
    return redirect('/admin/grants/draftgrantapplication/'+str(draft.pk)+'/')
  #GET
  return render(request, 'admin/grants/confirm_revert.html',
                {'application': submitted_app})

def AdminRollover(request, app_id):
  application = get_object_or_404(models.GrantApplication, pk=app_id)
  org = application.organization

  if request.method == 'POST':
    form = AdminRolloverForm(org, request.POST)
    if form.is_valid():
      cycle = get_object_or_404(models.GrantCycle, pk=int(form.cleaned_data['cycle']))
      logger.info('Success rollover of ' + unicode(application) +
                   ' to ' + str(cycle))
      application.pk = None # this + save makes new copy
      application.pre_screening_status = 10
      application.submission_time = timezone.now()
      application.grant_cycle = cycle
      application.cycle_question = ''
      application.budget = ''
      application.save()
      return redirect('/admin/grants/grantapplication/'+str(application.pk)+'/')
  else:
    form = AdminRolloverForm(org)
    cycle_count = str(form['cycle']).count('<option value')

  return render(request, 'admin/grants/rollover.html',
                {'form': form, 'application': application, 'count': cycle_count})

def Impersonate(request):

  if request.method == 'POST':
    form = LoginAsOrgForm(request.POST)
    if form.is_valid():
      org = form.cleaned_data['organization']
      return redirect('/apply/?user='+org)
  form = LoginAsOrgForm()
  return render(request, 'admin/grants/impersonate.html', {'form': form})

def grants_report(request):
  """ Handles grant reporting

  Displays all reporting forms
  Uses report type-specific methods to handle POSTs
  """

  app_form = AppReportForm()
  org_form = OrgReportForm()
  award_form = AwardReportForm()

  context = {'app_form': app_form,
             'org_form': org_form,
             'award_form': award_form}

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
    elif 'run-award' in request.POST:
      logger.info('Award report')
      form = AwardReportForm(request.POST)
      context['award_form'] = form
      context['active_form'] = '#award-form'
      results_func = get_award_results
    else:
      logger.error('Unknown report type')
      form = False

    if form and form.is_valid():
      options = form.cleaned_data
      logger.info('A valid form: ' + str(options))

      #get results
      field_names, results = results_func(options)

      #format results
      if options['format'] == 'browse':
        return render_to_response('grants/report_results.html',
                                  {'results': results, 'field_names': field_names})
      elif options['format'] == 'csv':
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % 'grantapplications'
        writer = unicodecsv.writer(response)
        writer.writerow(field_names)
        for row in results:
          writer.writerow(row)
        return response
    else:
      logger.warning('Invalid form!' + str(form.errors))

  context['app_base'] = 'submission time, organization name, grant cycle'
  context['award_base'] = 'organization name, amount, date check mailed'
  context['org_base'] = 'name'
  return render(request, 'grants/reporting.html', context)


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

  #initial queryset
  apps = models.GrantApplication.objects.order_by('-submission_time').select_related(
      'organization', 'grant_cycle')

  #filters
  min_year = datetime.datetime.strptime(options['year_min'] + '-01-01 00:00:01',
                                        '%Y-%m-%d %H:%M:%S')
  min_year = timezone.make_aware(min_year, timezone.get_current_timezone())
  max_year = datetime.datetime.strptime(options['year_max'] + '-12-31 23:59:59',
                                        '%Y-%m-%d %H:%M:%S')
  max_year = timezone.make_aware(max_year, timezone.get_current_timezone())
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
  if options['report_collab']:
    fields += models.GrantApplication.fields_starting_with('collab_ref')
  if options['report_racial_ref']:
    fields += models.GrantApplication.fields_starting_with('racial')
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
    #apps = apps.prefetch_related('grantaward_set') #TODO any replacement?
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
          convert = dict(models.PRE_SCREENING)
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
              award_col += '%s %s ' % (award.amount, papp.giving_project.title)
            except models.GivingProjectGrant.DoesNotExist:
              pass
          if get_gp_ss:
            if ss_col != '':
              ss_col += ', '
            if papp.screening_status:
              ss_col += '%s (%s) ' % (dict(models.SCREENING)[papp.screening_status],
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

def get_award_results(options):
  """ Fetch award (all types) report results

  Args:
    options: cleaned_data from a request.POST-filled instance of AwardReportForm

  Returns:
    A list of display-formatted field names. Example:
      ['Amount', 'Check mailed', 'Organization']

    A list of awards & related info. Each item is a list of requested values
    Example: [
        ['10000', '2013-10-23 09:08:56+0:00', 'Fancy pants org'],
        ['5987', '2011-08-04 09:08:56+0:00', 'Justice League']
      ]
  """

  # initial querysets
  gp_awards = models.GivingProjectGrant.objects.all().select_related('projectapp',
      'projectapp__application', 'projectapp__application__organization')
  sponsored = models.SponsoredProgramGrant.objects.all().select_related('organization')

  # filters
  min_year = datetime.datetime.strptime(options['year_min'] + '-01-01 00:00:01', '%Y-%m-%d %H:%M:%S')
  min_year = timezone.make_aware(min_year, timezone.get_current_timezone())
  max_year = datetime.datetime.strptime(options['year_max'] + '-12-31 23:59:59', '%Y-%m-%d %H:%M:%S')
  max_year = timezone.make_aware(max_year, timezone.get_current_timezone())
  gp_awards = gp_awards.filter(created__gte=min_year, created__lte=max_year)
  sponsored = sponsored.filter(entered__gte=min_year, entered__lte=max_year)

  if options.get('organization_name'):
    gp_awards = gp_awards.filter(projectapp__application__organization__name__contains=options['organization_name'])
    sponsored = sponsored.filter(organization__name__contains=options['organization_name'])
  if options.get('city'):
    gp_awards = gp_awards.filter(projectapp__application__organization__city=options['city'])
    sponsored = sponsored.filter(organization__city=options['city'])
  if options.get('state'):
    gp_awards = gp_awards.filter(projectapp__application__organization__state__in=options['state'])
    sponsored = sponsored.filter(organization__state__in=options['state'])
  if options.get('has_fiscal_sponsor'):
    gp_awards = gp_awards.exclude(projectapp__application__organization__fiscal_org='')
    sponsored = sponsored.exclude(organization__fiscal_org='')

  # fields
  fields = ['check_mailed', 'amount', 'organization', 'grant_type', 'giving_project']
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
      elif field == 'grant_type':
        row.append('Giving project')
      elif field == 'giving_project':
        row.append(award.projectapp.giving_project.title)
      elif field == 'year_end_report_due':
        row.append(award.yearend_due())
      elif field == 'id':
        row.append('') # only for sponsored
      else:
        row.append(getattr(award, field, ''))
    for field in org_fields:
      row.append(getattr(award.projectapp.application.organization, field))
    results.append(row)
  for award in sponsored:
    row = []
    for field in fields:
      if field == 'grant_type':
        row.append('Sponsored program')
      elif hasattr(award, field):
        row.append(getattr(award, field))
      else:
        row.append('')
    for field in org_fields:
      row.append(getattr(award.organization, field))
    results.append(row)

  field_names = [f.capitalize().replace('_', ' ') for f in fields]
  field_names += ['Org. '+ f.capitalize().replace('_', ' ') for f in org_fields]

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
  if reg == True:
    orgs = orgs.exclude(email="")
  elif reg == False:
    org = orgs.filter(email="")
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

  field_names = [f.capitalize().replace('_', ' ') for f in fields] #for display

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
              awards_str += '$%s %s %s' % (award.amount, award.projectapp.giving_project.title, timestamp)
              awards_str += linebreak
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

# CRON

def DraftWarning(request):
  """ Warn orgs of impending draft freezes
      NOTE: must run exactly once a day
      Gives 7 day warning if created 7+ days before close, otherwise 3 day warning """

  drafts = models.DraftGrantApplication.objects.all()
  eight = datetime.timedelta(days=8)

  for draft in drafts:
    time_left = draft.grant_cycle.close - timezone.now()
    created_offset = draft.grant_cycle.close - draft.created
    if (created_offset > eight and eight > time_left > datetime.timedelta(days=7)) or (created_offset < eight and datetime.timedelta(days=2) < time_left <= datetime.timedelta(days=3)):
      subject, from_email = 'Grant cycle closing soon', constants.GRANT_EMAIL
      to = draft.organization.email
      html_content = render_to_string('grants/email_draft_warning.html',
                                      {'org': draft.organization, 'cycle': draft.grant_cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to],
                                   [constants.SUPPORT_EMAIL])
      msg.attach_alternative(html_content, 'text/html')
      msg.send()
      logger.info('Email sent to ' + to + 'regarding draft application soon to expire')
  return HttpResponse("")

def yer_reminder_email(request):
  """ Remind orgs of upcoming year end reports that are due
      NOTE: Must run exactly once a day
      Sends reminder emails at 1 month and 1 week """

  # get awards due in 7 or 30 days by agreement_returned date
  year_ago = timezone.now().date().replace(year=timezone.now().year - 1)
  award_dates = [year_ago + datetime.timedelta(days=30), year_ago + datetime.timedelta(days=7)]
  awards = (models.GivingProjectGrant.objects.select_related()
                                             .prefetch_related('yearendreport')
                                             .filter(agreement_mailed__in=award_dates))

  return send_yer_email(awards, 'grants/email_yer_due.html')


def send_yer_email(awards, template):

  for award in awards:
    if not hasattr(award, 'yearendreport'):
      app = award.projectapp.application

      subject = 'Year end report'
      from_email = constants.GRANT_EMAIL
      to_email = app.organization.email
      html_content = render_to_string(template, {
        'award': award, 'app': app, 'gp': award.projectapp.giving_project,
        'base_url': constants.APP_BASE_URL
      })
      text_content = strip_tags(html_content)

      msg = EmailMultiAlternatives(subject, text_content, from_email,
                                   [to_email], [constants.SUPPORT_EMAIL])
      msg.attach_alternative(html_content, 'text/html')
      msg.send()
      logger.info('YER reminder email sent to %d for award %d', to_email, award.pk)

  return HttpResponse('success')

# UTILS
# (in views because it caused import problems when in utils.py)
def GetFileURLs(request, app, printing=False):
  """ Get viewing urls for the files in a given app or year-end report, draft or final

    Args:
      app: one of GrantApplication, DraftGrantApplication, YearEndReport, YERDraft

    Returns:
      a dict of urls for viewing each file, taking into account whether it can
        be viewed in google doc viewer
      keys are the name of the django model fields. i.e. budget, budget1, funding_sources

    Raises:
      returns an empty dict if the given object is not valid
  """
  app_urls = {'funding_sources': '', 'demographics': '', 'fiscal_letter': '', 'budget1': '',
              'budget2': '', 'budget3': '', 'project_budget_file': ''}
  report_urls = {'photo1': '', 'photo2': '', 'photo3': '', 'photo4': '', 'photo_release': ''}


  base_url = request.build_absolute_uri('/')


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
    logger.error('GetFileURLs received invalid object')
    return {}

  #check file fields, compile links
  for field in file_urls:
    value = getattr(app, field)
    if value:
      ext = value.name.lower().split('.')[-1]
      file_urls[field] += base_url + str(app.pk) + u'-' + field + u'.' + ext
      if not settings.DEBUG and ext in constants.VIEWER_FORMATS: #doc viewer
        if printing:
          if not (ext == 'xls' or ext == 'xlsx'):
            file_urls[field] = 'https://docs.google.com/viewer?url=' + file_urls[field]
        else:
          file_urls[field] = ('https://docs.google.com/viewer?url=' +
                              file_urls[field] + '&embedded=true')
  logger.debug(file_urls)
  return file_urls

def update_profile(request, org_id):
  # TODO this should be a command

  message = ''
  org = get_object_or_404(models.Organization, pk=org_id)

  apps = org.grantapplication_set.all()
  if apps:
    profile_data = model_to_dict(apps[0])
    logger.info(profile_data)
    form = OrgProfile(profile_data, instance=org)
    if form.is_valid():
      form.save()
      if apps[0].fiscal_letter:
        org.fiscal_letter = apps[0].fiscal_letter
        org.save()
      message = 'Organization profile updated.'
    else:
      message = 'Form not valid. Could not update'
  else:
    message = 'This org has no applications. Nothing to update'

  return HttpResponse(message)
