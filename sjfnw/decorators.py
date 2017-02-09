from functools import wraps

from django.http import HttpResponse
from django.utils.decorators import available_attrs

def login_required_ajax(login_url):
  """ ajax-compatible version of login_required decorator """

  def decorator(view_func):

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):

      if request.user.is_authenticated():
        return view_func(request, *args, **kwargs)
      else:
        return HttpResponse(login_url, status=401)

    return _wrapped_view
  return decorator
