# encoding: utf-8

import logging, re, string

from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone

from google.appengine.ext import blobstore

from sjfnw.grants import constants as gc

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

  value = file_field.name if hasattr(file_field, 'name') else file_field
  key = value.split('/', 1)[0]
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

# Utils for handling multi-widget form fields
#
# Values for these fields exist in 3 formats:

# A. One key for each widget, inside a bigger dict
#    Draft `contents` uses this format because the server receives data in
#    this format for draft autosave calls
#    Example: { ... 'timeline_0': 'a', 'timeline_1': 'b', ... }
#
# B. Array of values
#    Easiest way to pass values into form.
#    Used internally by MultiWidget classes
#
# C. Single list or dict, stored as json string
#    Once the app is submitted, this format is used for NarrativeAnswer
#    (In some cases - timeline - this is just json.dumps(B))

def group_multiwidget_values(data, name):
  """ Collect values for <name> and put them ina list under a single key. A -> B
    Args:
      data - dict to use/modify
      name - name of field
    Returns: json string of list of values
  """
  if name in data:
    logger.warn('%s is already present in dict', name)
    return

  collection = []
  i = 0
  key = '{}_{}'.format(name, i)
  while key in data:
    collection.append(data[key])
    i += 1
    key = '{}_{}'.format(name, i)
  return collection

def flatten_references(refs):
  """ Convert references from DB format to a flat array. C -> B
    Args: refs - List of references. Example: [
        {'name': 'Abby', 'org': 'NDMF', 'phone': '', 'email': 'abby@ndmf.com'}
        {'name': 'Edü', 'org': 'Pøl', 'phone': '555-4938', 'email': ''}
      ]
    Returns: list of values. Example: [
      'Abby', 'NDMF', '', 'abby@ndmf.com', 'Edü', 'Pøl', 555-4938', ''
    ]
  """
  result = []
  for ref in refs:
    result += [ref['name'], ref['org'], ref['phone'], ref['email']]
  return result

def multiwidget_list_to_dict(values, field_name):
  """ Convert flat list into separate keys (draft contents format) B -> A
    Args:
      values - list of values for multiwidget field
      field_name
  """
  result = {}
  for i, item in enumerate(values):
    result['{}_{}'.format(field_name, i)] = item
  return result

def format_references(data, name):
  """ Extract references from form data and reformat for DB. A -> C
    Args:
      data - dict, e.g. autosave POST dict
      name - name of field. 'racial_justice_references' or 'collaboration_references'
    Returns: list of references in dict format
  """

  values = []
  for i in [0, 1]:
    start = i * 4
    values.append({
      'name': data.get(u'{}_{}'.format(name, start), ''),
      'org': data.get(u'{}_{}'.format(name, start + 1), ''),
      'phone': data.get(u'{}_{}'.format(name, start + 2), ''),
      'email': data.get(u'{}_{}'.format(name, start + 3), '')
    })
  return values

def format_draft_contents(contents):
  """ Consolidate multi-widget values into an array of values per field """
  contents['timeline'] = group_multiwidget_values(contents, 'timeline')
  for name in ['collaboration_references', 'racial_justice_references']:
    contents[name] = group_multiwidget_values(contents, name)

def has_allowed_file_ext(value):
  return value and value.lower().split('.')[-1] in gc.ALLOWED_FILE_TYPES

def has_allowed_photo_file_ext(value):
  return value and value.lower().split('.')[-1] in gc.PHOTO_FILE_TYPES
