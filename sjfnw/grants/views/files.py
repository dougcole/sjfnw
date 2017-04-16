import logging

from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone

from google.appengine.ext import blobstore

from sjfnw.grants import models
from sjfnw.grants.utils import find_blobinfo, get_user_override
from sjfnw.grants.views.helpers import get_file_urls

logger = logging.getLogger('sjfnw')

LOGIN_URL = '/apply/login/'

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
