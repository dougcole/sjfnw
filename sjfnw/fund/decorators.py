from functools import wraps
import logging

from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import available_attrs

logger = logging.getLogger('sjfnw')


def require_member(require_membership=False):
  """ Require request.user that is authenticed, active and has associated member

      If require_membership is True, require that the member is on an approved membership
  """
  def decorator(view_func):

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):

      if not request.user.is_authenticated():
        return redirect_to_login(request.get_full_path(),
                                 reverse('sjfnw.fund.views.fund_login'))
      elif not request.user.is_active:
        logger.warn('Inactive member %s', request.user.username)
        # TODO error page
        return HttpResponse('Something is wrong')

      elif not hasattr(request.user, 'member'):
        logger.debug('Not a member: %s', request.user.username)
        return redirect(reverse('sjfnw.fund.views.not_member'))

      if require_membership:
        membership = None
        if request.user.member.current:
          membership = (request.user.member.membership_set
                                           .filter(pk=request.user.member.current)
                                           .first())
        if not membership:
          return redirect(reverse('sjfnw.fund.views.manage_account'))

        elif not membership.approved:
          return redirect(reverse('sjfnw.fund.views.not_approved'))

        request.membership = membership

      return view_func(request, *args, **kwargs)
    return _wrapped_view
  return decorator
