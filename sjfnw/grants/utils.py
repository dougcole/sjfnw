# encoding: utf-8

import logging, re, string

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, Http404
from django.utils import timezone

from google.appengine.ext import blobstore

logger = logging.getLogger('sjfnw')

def get_user_override(request):
  username = request.GET.get('user')
  return '?user=' + username if username else ''

def strip_punctuation_and_non_ascii(input_str):
  """ Remove all non-ascii characters. Used for word counts in forms """
  input_str = unicode(input_str) # input may or may not be unicode already
  return ''.join([c for c in input_str if c not in string.punctuation and ord(c) < 128])

def local_date_str(timestamp):
  """ Convert UTC timestamp to local date string in mm/dd/yyyy format """
  timestamp = timezone.localtime(timestamp)
  return timestamp.strftime('%m/%d/%Y')

def get_blobkey_from_body(body):
  """ Extract blobkey from request.body """

  if settings.DEBUG: # on dev server, has quotes around it
    key = re.search(r'blob-key="([^"\s]*)"', body)
  else:
    key = re.search(r'blob-key=(\S*)', body)

  key = key.group(1) if key else None
  logger.info('Extracted blobkey from request.body: %s', key)
  return key

def find_blobinfo(file_field, hide_errors=False):
  """Given contents of a file field, return BlobInfo. """

  key = file_field.name.split('/', 1)[0]
  if key:
    blobinfo = blobstore.BlobInfo.get(key)
    if blobinfo:
      logger.info('Found blobinfo. Filename: %s, size: %s, content-type: %s',
                  blobinfo.filename, blobinfo.size, blobinfo.content_type)
      return blobinfo

  if hide_errors:
    return
  else:
    raise Http404('Blobinfo not found')

def delete_blob(file_field):
  if not file_field:
    logger.warn('Missing file_field argument')
    return

  blobinfo = find_blobinfo(file_field, hide_errors=True)
  if blobinfo is not None:
    blobinfo.delete()
    logger.info('Blob deleted')
    return HttpResponse('deleted')
  else:
    return HttpResponse('nothing deleted')

def flatten_references(refs):
  result = []
  for ref in refs:
    result += [ref['name'], ref['org'], ref['phone'], ref['email']]
  return result
