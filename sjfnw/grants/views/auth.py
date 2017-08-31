import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login

from sjfnw.grants.forms.auth import LoginForm, RegisterForm

logger = logging.getLogger('sjfnw')

def org_login(request):
  if request.method == 'POST':
    form = LoginForm(request.POST)
    if form.is_valid():
      email = request.POST['email'].lower()
      password = request.POST['password']
      user = authenticate(username=email, password=password)
      if user:
        if user.is_active:
          login(request, user)
          return redirect(org_home)
        else:
          logger.warning('Inactive org account tried to log in, username: ' + email)
          messages.error(request, 'Your account is inactive. Please contact an administrator.')
      else:
        messages.error(request, 'Your password didn\'t match the one on file. Please try again.')
  else:
    form = LoginForm()
  register = RegisterForm()
  return render(request, 'grants/org_login_register.html', {
      'form': form, 'register': register
  })

def org_register(request):

  if request.method == 'GET':
    register = RegisterForm()

  elif request.method == 'POST':
    register = RegisterForm(request.POST)

    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']
      org_name = request.POST['organization']

      try:
        org = models.Organization.objects.create_with_user(username_email,
            password=password, name=org_name)
      except ValueError as err:
        logger.warning(username_email + ' tried to re-register as org')
        login_link = utils.create_link(reverse('sjfnw.grants.views.org_login'), 'Login')
        messages.error(request, '{} {} instead.'.format(err.message, login_link))

      else:
        user = authenticate(username=username_email, password=password)
        if user:
          if user.is_active:
            login(request, user)
            return redirect(org_home)
          else:
            logger.info('Registration needs admin approval, showing message. ' +
                username_email)
            messages.warning(request, 'You have registered successfully but your account '
            'needs administrator approval. Please contact '
            '<a href="mailto:info@socialjusticefund.org">info@socialjusticefund.org</a>')
        else:
          messages.error(request, 'There was a problem with your registration. '
              'Please <a href=""/apply/support#contact">contact a site admin</a> for assistance.')
          logger.error('Password not working at registration, account:  ' + username_email)

  form = LoginForm()

  return render(request, 'grants/org_login_register.html', {
    'form': form, 'register': register
  })

def not_registered(request):

  if not request.user.is_authenticated():
    return redirect(LOGIN_URL)

  username = request.GET.get('user') or request.user.username

  return render(request, 'grants/not_registered.html', {'username': username})

