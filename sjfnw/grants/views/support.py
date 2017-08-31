from django.shortcuts import render

from sjfnw import constants as c

def org_support(request):
  return render(request, 'grants/org_support.html', {
    'support_email': c.SUPPORT_EMAIL,
    'support_form': c.GRANT_SUPPORT_FORM
  })


