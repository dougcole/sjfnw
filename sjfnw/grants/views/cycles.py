import logging, re, urllib2

from django.http import Http404
from django.shortcuts import get_object_or_404, render

from sjfnw import utils
from sjfnw.grants.models import GrantCycle

logger = logging.getLogger('sjfnw')

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

  cycle = get_object_or_404(GrantCycle, pk=cycle_id)

  if not cycle.info_page:
    raise Http404

  content = _fetch_cycle_info(cycle.info_page)

  return render(request, 'grants/cycle_info.html', {
    'cycle': cycle, 'content': content
  })
