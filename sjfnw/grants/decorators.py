from functools import wraps
import logging

from django.http import HttpResponse
from django.utils.decorators import available_attrs
from django.shortcuts import redirect

from sjfnw.grants.models import Organization
from sjfnw.grants.utils import get_user_override

logger = logging.getLogger('sjfnw')

def registered_org():
  """ Requires that the logged in user corresponds to an Organization and
      passes that organization as an arg to the view

    Notes:
      - Must be used *after* @login_required
      - If no org is found matching user email, returns 401 or redirects to /apply/nr
      - Works with staff override, indicates in log
  """

  def decorator(view_func):

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
      username = request.user.username
      if request.user.is_staff and request.GET.get('user'): # staff override
        username = request.GET.get('user')
        logger.info('Staff override - %s logging in as %s', request.user.username, username)
      try:
        organization = Organization.objects.get(user__username=username)
        logger.info(u'Organization: %s', organization.name)
        return view_func(request, organization, *args, **kwargs)
      except Organization.DoesNotExist:
        logger.info('No organization found matching username %s', username)
        url = '/apply/nr' + get_user_override(request)
        return HttpResponse(url, status=401) if request.is_ajax() else redirect(url)

    return _wrapped_view

  return decorator
