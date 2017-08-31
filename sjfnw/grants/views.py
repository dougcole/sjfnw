from datetime import timedelta
import json, logging, re, urllib2

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from google.appengine.ext import blobstore

from sjfnw import constants as c, utils
from sjfnw.decorators import login_required_ajax
from sjfnw.fund.models import Member
from sjfnw.grants import constants as gc
from sjfnw.grants import models
from sjfnw.grants.decorators import registered_org
from sjfnw.grants.forms.admin import (AdminRolloverForm, AppReportForm,
 GPGrantReportForm, LoginAsOrgForm, OrgMergeForm, OrgReportForm,
 SponsoredAwardReportForm)
from sjfnw.grants.forms.org_tools import RolloverForm, RolloverYERForm
from sjfnw.grants.modelforms import get_form_for_cycle, YearEndReportForm
from sjfnw.grants.utils import (local_date_str, find_blobinfo,
    get_user_override, format_draft_contents)

logger = logging.getLogger('sjfnw')

LOGIN_URL = '/apply/login/'

# -----------------------------------------------------------------------------
#  Org home page tools
# -----------------------------------------------------------------------------

def _is_valid_rollover_target(source, target_cycle):
  return source.grant_cycle.get_type() == target_cycle.get_type()

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
