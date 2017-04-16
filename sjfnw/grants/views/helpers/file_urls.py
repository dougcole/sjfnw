import logging

from django.conf import settings

from sjfnw.grants import constants as gc
from sjfnw.grants.models import (DraftGrantApplication, GrantApplication,
    YearEndReport, YERDraft)

logger = logging.getLogger('sjfnw')

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
  if isinstance(app, GrantApplication):
    base_url += 'grants/app-file/'
    file_urls = app_urls
    file_urls['budget'] = ''
  elif isinstance(app, DraftGrantApplication):
    file_urls = app_urls
    base_url += 'grants/adraft-file/'
  elif isinstance(app, YearEndReport):
    file_urls = report_urls
    base_url += 'grants/report-file/'
  elif isinstance(app, YERDraft):
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
