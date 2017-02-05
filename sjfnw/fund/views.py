import datetime, logging, os, json

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.urlresolvers import reverse
from django.forms.formsets import formset_factory
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.http import is_safe_url

from google.appengine.ext import deferred, ereporter

from sjfnw import constants as c, utils
from sjfnw.fund.decorators import require_member
from sjfnw.fund import forms, modelforms, models
from sjfnw.grants.models import Organization, ProjectApp

if not settings.DEBUG:
  ereporter.register_logger()

logger = logging.getLogger('sjfnw')

# ----------------------------------------------------------------------------
#  MAIN VIEWS
# ----------------------------------------------------------------------------

@require_member(require_membership=True)
def home(request):
  """ Handles display of the home/personal page

  Redirects:
    no contacts -> copy_contacts or add_mult
    contacts without estimates + post-training + no url params -> add_estimates

  Handles display of
    Top blocks
    Charts of personal progress
    List of donors, with details and associated steps
    Url param can trigger display of a form on a specific donor/step
  """

  membership = request.membership

  # check for survey
  surveys = (models.GPSurvey.objects
      .filter(giving_project=membership.giving_project, date__lte=timezone.now())
      .exclude(id__in=json.loads(membership.completed_surveys))
      .order_by('date'))

  if surveys:
    logger.info('Needs to fill out survey; redirecting')
    return redirect(reverse('sjfnw.fund.views.project_survey', kwargs={
      'gp_survey_id': surveys[0].pk
    }))

  # check if they have contacts
  donors = membership.donor_set.prefetch_related('step_set')
  if not donors:
    if not membership.copied_contacts:
      all_donors = models.Donor.objects.filter(membership__member=membership.member)
      if all_donors:
        logger.info('Eligible to copy contacts; redirecting')
        return redirect(copy_contacts)
    return redirect(add_mult)

  # check whether they need to add estimates
  if (membership.giving_project.require_estimates() and
      donors.filter(amount__isnull=True)):
    return redirect(add_estimates)

  # from here we know we're not redirecting

  # top content
  _, news, grants = _get_block_content(membership, get_steps=False)
  header = membership.giving_project.title

  # handle notifications - only show once unless DEBUG is on
  notif = membership.notifications
  if notif and not settings.DEBUG:
    logger.info('Displaying notification to %s: %s', unicode(membership), notif)
    membership.notifications = ''
    membership.save(skip=True)

  # compile steps and progress metrics
  progress, incomplete_steps = _compile_membership_progress(donors)
  donors = sorted(donors, key=_get_converted_date)

  # suggested steps for step forms
  suggested = membership.giving_project.get_suggested_steps()

  # parse url params
  step = request.GET.get('step')
  donor = request.GET.get('donor')
  form_type = request.GET.get('t')
  load_form = request.GET.get('load')
  if step and donor and form_type:
    load = '/fund/' + donor + '/' + step
    if form_type == 'complete':
      load += '/done'
    loadto = donor + '-nextstep'
  elif load_form == 'stepmult':
    load = '/fund/stepmult'
    loadto = 'addmult'
  else: # no form specified
    load = ''
    loadto = ''

  return render(request, 'fund/home.html', {
    '1active': 'true', 'header': header, 'news': news, 'grants': grants,
    'steps': incomplete_steps, 'donors': donors, 'progress': progress,
    'notif': notif, 'suggested': suggested, 'load': load, 'loadto': loadto
  })

def _get_converted_date(donor):
  """ Use future date for donors without next step so they'll get sorted to the end """
  if hasattr(donor, 'next_step'):
    return donor.next_step.date
  return datetime.date(2100, 01, 01)


def _compile_membership_progress(donors):
  """ Go through membership's donors and steps, compiling progress metrics
    and organizing steps based on completion

    Adds summary attribute to donors (and others via donor.organize_steps)

    Returns:
      progress - dict, see progress dict definition below
      incomplete_steps - list of incomplete Steps for this membership
  """
  progress = {
    'contacts': len(donors),
    'contacts_remaining': len(donors),
    'estimated': 0,
    'talked': 0,
    'asked': 0,
    'promised': 0,
    'received': 0
  }

  if not donors:
    logger.error('Membership has no contacts but wasn\'t redirected to add_mult')
    return progress, []

  # compile progress metrics and donor summaries
  for donor in donors:
    donor.summary = ''

    if donor.asked:
      progress['asked'] += 1
      donor.summary = 'Asked. '
    elif donor.talked:
      progress['talked'] += 1

    progress['estimated'] += donor.estimated()

    if donor.received() > 0:
      donor.summary += ' $%s received by SJF.' % intcomma(donor.received())
      progress['received'] += donor.received()
      if donor.received() < donor.total_promised():
        progress['promised'] += donor.total_promised() - donor.received()
    elif donor.promised:
      donor.summary += ' Total promised $%s.' % intcomma(donor.total_promised())
      progress['promised'] += donor.total_promised()
    elif donor.asked:
      if donor.promised == 0:
        donor.summary += ' Declined to donate.'
      else:
        donor.summary += ' Awaiting response.'

  # progress chart calculations
  if progress['contacts'] > 0:
    amount_raised = progress['promised'] + progress['received']
    progress['contacts_remaining'] = progress['contacts'] - progress['talked'] - progress['asked']
    progress['togo'] = max(progress['estimated'] - amount_raised, 0)
    if progress['togo'] > 0:
      progress['header'] = '${} fundraising goal'.format(intcomma(progress['estimated']))
    else:
      progress['header'] = '${} raised'.format(intcomma(amount_raised))

  # process steps; compile incompletes
  incomplete_steps = []
  for donor in donors:
    donor.organize_steps()
    if hasattr(donor, 'next_step'):
      incomplete_steps.append(donor.next_step)
  incomplete_steps.sort(key=lambda step: step.date)

  return progress, incomplete_steps


@require_member(require_membership=True)
def project_page(request):

  membership = request.membership
  project = membership.giving_project

  steps, news, grants = _get_block_content(membership)
  header = project.title

  # project metrics/progress
  progress = {'contacts': 0, 'talked': 0, 'asked': 0, 'promised': 0, 'received': 0}
  donors = list(models.Donor.objects.filter(membership__giving_project=project))
  progress['contacts'] = len(donors)
  for donor in donors:
    donor.summary = []
    if donor.asked:
      progress['asked'] += 1
    elif donor.talked:
      progress['talked'] += 1
    if donor.received() > 0:
      progress['received'] += donor.received()
    elif donor.promised:
      progress['promised'] += donor.total_promised()

  progress['contacts_remaining'] = progress['contacts'] - progress['talked'] - progress['asked']
  progress['togo'] = project.fund_goal - progress['promised'] - progress['received']
  if progress['togo'] < 0:
    progress['togo'] = 0

  # project resources
  resources = (models.ProjectResource.objects.filter(giving_project=project)
                                             .select_related('resource')
                                             .order_by('session'))

  return render(request, 'fund/project.html', {
    '2active': 'true', 'header': header, 'news': news, 'grants': grants,
    'steps': steps, 'project_progress': progress, 'resources': resources
  })


@require_member(require_membership=True)
def grant_list(request):

  membership = request.membership
  project = membership.giving_project

  # blocks
  steps, news, grants = _get_block_content(membership)

  # base
  header = project.title

  return render(request, 'fund/grants.html', {
    '3active': 'true', 'header': header, 'news': news, 'steps': steps,
    'membership': membership, 'grants': grants
  })

# ----------------------------------------------------------------------------
#  LOGIN & REGISTRATION
# ----------------------------------------------------------------------------

def fund_login(request):
  error_msg = ''
  redirect_to = request.POST.get('next', request.GET.get('next', ''))

  if request.method == 'POST':
    form = forms.LoginForm(request.POST)
    if form.is_valid():
      username = request.POST['email'].lower()
      password = request.POST['password']
      user = auth.authenticate(username=username, password=password)
      if user:
        if not hasattr(user, 'member'):
          return redirect(reverse('sjfnw.fund.views.not_member'))
        elif user.is_active:
          auth.login(request, user)
          if not redirect_to or not is_safe_url(url=redirect_to, host=request.get_host()):
            redirect_to = home
          return redirect(redirect_to)
        else:
          error_msg = 'Your account is not active.  Contact an administrator.'
          logger.warning('Inactive account tried to log in. Username: ' + username)
      else:
        error_msg = 'Your login and password didn\'t match.'
      logger.info(error_msg)

  else:
    form = forms.LoginForm()

  return render(request, 'fund/login.html', {
    'form': form, 'error_msg': error_msg, 'redirect_to': redirect_to
  })


def fund_register(request):
  error_msg = ''
  if request.method == 'POST':
    register = forms.RegistrationForm(request.POST)
    if register.is_valid():

      username_email = request.POST['email'].lower()
      password = request.POST['password']
      first_name = request.POST['first_name']
      last_name = request.POST['last_name']

      try:
        member = models.Member.objects.create_with_user(username_email, password=password,
            first_name=first_name, last_name=last_name)
      except ValueError as err:
        logger.warning(username_email + ' tried to re-register')
        login_link = utils.create_link('/fund/login/', 'Login')
        error_msg = '{} {} instead.'.format(err.message, login_link)

      if not error_msg:
        logger.info('Registration - user and member objects created for ' + username_email)
        # if they specified a GP, create Membership
        membership = None
        if request.POST['giving_project']:
          giv = models.GivingProject.objects.get(pk=request.POST['giving_project'])
          notif = ('<table><tr><td>Welcome to Project Central!<br>'
              'I\'m Odo, your Online Donor Organizing assistant. I\'ll be here to '
              'guide you through the fundraising process and cheer you on.</td>'
              '<td><img src="/static/images/odo1.png" height=88 width=54 alt="Odo waving">'
              '</td></tr></table>')
          membership, _ = _create_membership(member, giv, notif=notif)
          logger.info('Registration - membership in %s created, welcome message set', unicode(giv))

        # try to log in
        user = auth.authenticate(username=username_email, password=password)
        if user:
          if user.is_active:
            # success! log in and redirect
            auth.login(request, user)
            if not membership:
              return redirect(manage_account)
            if membership.approved:
              return redirect(home)
            return render(request, 'fund/registered.html', {
              'member': member, 'proj': giv
            })
          else: # not active
            error_msg = 'Your account is not active. Please contact a site admin for assistance.'
            logger.error('Inactive right after registering. Email: ' + username_email)
        else: # email & pw didn't match
          error_msg = ('There was a problem with your registration.  Please '
              '<a href="/fund/support# contact">contact a site admin</a> for assistance.')
          logger.error('Password didn\'t match right after registering. Email: %s',
              username_email)

  else: # GET
    register = forms.RegistrationForm()

  return render(request, 'fund/register.html', {
    'form': register, 'error_msg': error_msg
  })

# ----------------------------------------------------------------------------
#  MEMBERSHIP MANAGEMENT
# ----------------------------------------------------------------------------

@require_member()
def manage_account(request):

  member = request.user.member

  ships = member.membership_set.all()

  error_msg = ''
  if request.method == 'POST':
    form = forms.AddProjectForm(request.POST)
    if form.is_valid():
      logger.debug('Valid add project')
      gp_id = request.POST['giving_project']
      gp = models.GivingProject.objects.get(pk=gp_id)
      membership, error_msg = _create_membership(member, gp)
      if membership and not error_msg:
        if membership.approved:
          return redirect(home)
        return render(request, 'fund/registered.html', {
          'member': member, 'proj': gp
        })
  else: # GET
    form = forms.AddProjectForm()

  return render(request, 'fund/account_projects.html', {
    'member': member, 'form': form, 'custom_error': error_msg, 'ships': ships
  })


@require_member()
def set_current(request, ship_id):
  """ Triggered when a user clicks on a non-current membership from their
      manage_account view """
  member = request.user.member
  try:
    ship = models.Membership.objects.get(pk=ship_id, member=member, approved=True)
  except models.Membership.DoesNotExist:
    return redirect(manage_account)

  member.current = ship.pk
  member.save()

  return redirect(home)

# ----------------------------------------------------------------------------
#  ERROR & HELP PAGES
# ----------------------------------------------------------------------------

@login_required(login_url='/fund/login')
def not_member(request):
  org = Organization.objects.filter(email=request.user.username).first()

  return render(request, 'fund/not_member.html', {
    'contact_url': '/fund/support#contact', 'org': org
  })


@require_member()
def not_approved(request):
  if not hasattr(request.user, 'member'):
    return redirect(not_member)

  return render(request, 'fund/not_approved.html')


def blocked(request):
  return render(request, 'fund/blocked.html', {
    'contact_url': '/fund/support#contact'
  })


def support(request):
  member = getattr(request.user, 'member', None)

  return render(request, 'fund/support.html', {
    'member': member, 'support_email': c.SUPPORT_EMAIL,
    'support_form': c.FUND_SUPPORT_FORM
  })

# ----------------------------------------------------------------------------
#  SURVEY
# ----------------------------------------------------------------------------

@require_member(require_membership=True)
def project_survey(request, gp_survey_id):

  try:
    gp_survey = models.GPSurvey.objects.get(pk=gp_survey_id)
  except models.GPSurvey.DoesNotExist:
    logger.error('GP Survey does with given id does not exist.')
    raise Http404('survey not found')

  if request.method == 'POST':
    logger.info(request.POST)
    form = modelforms.SurveyResponseForm(gp_survey.survey, request.POST)
    if form.is_valid():
      form.save()
      logger.info('survey response saved')
      completed = json.loads(request.membership.completed_surveys)
      completed.append(gp_survey.pk)
      request.membership.completed_surveys = json.dumps(completed)
      request.membership.save()
      return HttpResponse('success')

  else: # GET
    form = modelforms.SurveyResponseForm(gp_survey.survey,
                                         initial={'gp_survey': gp_survey})

  steps, news, grants = _get_block_content(request.membership)

  return render(request, 'fund/forms/gp_survey.html', {
    'form': form, 'survey': gp_survey.survey, 'news': news,
    'steps': steps, 'grants': grants
  })

# ----------------------------------------------------------------------------
#  CONTACTS
# ----------------------------------------------------------------------------

@require_member(require_membership=True)
def copy_contacts(request):

  # base formset
  copy_formset = formset_factory(forms.CopyContacts, extra=0)

  if request.method == 'POST':
    logger.info(request.POST)

    if 'skip' in request.POST:
      logger.info('User skipping copy contacts')
      request.membership.copied_contacts = True
      request.membership.save()
      return HttpResponse('success')

    else:
      formset = copy_formset(request.POST)
      logger.info('Copy contracts submitted')
      if formset.is_valid():
        for form in formset.cleaned_data:
          if form['select']:
            contact = models.Donor(membership=request.membership,
                firstname=form['firstname'], lastname=form['lastname'],
                phone=form['phone'], email=form['email'], notes=form['notes'])
            contact.save()
            logger.debug('Contact created')
        request.membership.copied_contacts = True
        request.membership.save()
        return HttpResponse('success')
      else: # invalid
        logger.warning('Copy formset somehow invalid?! ' + str(request.POST))
        logger.warning(formset.errors)

  else: # GET
    all_donors = (models.Donor.objects.filter(membership__member=request.membership.member)
                                      .order_by('firstname', 'lastname', '-added'))

    # extract name, contact info, notes. handle duplicates
    initial_data = []
    for donor in all_donors:
      if (initial_data and donor.firstname == initial_data[-1]['firstname'] and
             (donor.lastname and donor.lastname == initial_data[-1]['lastname'] or
                 donor.phone and donor.phone == initial_data[-1]['phone'] or
                 donor.email and donor.email == initial_data[-1]['email'])):
        logger.info('Duplicate found! ' + str(donor))
        initial_data[-1]['lastname'] = initial_data[-1]['lastname'] or donor.lastname
        initial_data[-1]['phone'] = initial_data[-1]['phone'] or donor.phone
        initial_data[-1]['email'] = initial_data[-1]['email'] or donor.email
        initial_data[-1]['notes'] += donor.notes
        initial_data[-1]['notes'] = initial_data[-1]['notes'][:253] # cap below field char limit

      else: # not duplicate; add a row
        initial_data.append({
          'firstname': donor.firstname, 'lastname': donor.lastname,
          'phone': donor.phone, 'email': donor.email, 'notes': donor.notes
        })

    logger.debug('Loading copy contacts formset')
    logger.info('Initial data list of ' + str(len(initial_data)))
    formset = copy_formset(initial=initial_data)

  return render(request, 'fund/forms/copy_contacts.html', {'formset': formset})

@require_member(require_membership=True)
def add_mult(request):
  """ Add multiple contacts, with or without estimates

    If a user enters duplicates (same first & last name), they'll get a
      confirmation form before donors are saved

    GET is via redirect from home, and should render top blocks as well as form
    POST will be via AJAX and does not need block info
  """
  membership = request.membership

  est = membership.giving_project.require_estimates()
  if est:
    contact_formset = formset_factory(forms.MassDonor, extra=5)
  else:
    contact_formset = formset_factory(forms.MassDonorPre, extra=5)

  empty_error = u''

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save()

    formset = contact_formset(request.POST)

    if formset.is_valid():

      if formset.has_changed():
        logger.info('AddMult valid formset')

        # get list of existing donors to check for duplicates
        donors = models.Donor.objects.filter(membership=membership)
        donors = [unicode(donor) for donor in donors]
        duplicates = []

        for form in formset.cleaned_data:
          if form: # ignore blank rows
            confirm = form['confirm'] and form['confirm'] == '1'

            if not confirm and (form['firstname'] + ' ' + form['lastname'] in donors):
              # this entry is a duplicate that has not yet been confirmed
              initial = {'firstname': form['firstname'],
                         'lastname': form['lastname'],
                         'confirm': u'1'}
              if est:
                initial['amount'] = form['amount']
                initial['likelihood'] = form['likelihood']
              duplicates.append(initial)

            else: # not a duplicate
              if est:
                contact = models.Donor(membership=membership,
                    firstname=form['firstname'], lastname=form['lastname'],
                    amount=form['amount'], likelihood=form['likelihood'])
              else:
                contact = models.Donor(membership=membership,
                    firstname=form['firstname'], lastname=form['lastname'])
              contact.save()
              logger.info('contact created')

        if duplicates:
          logger.info('Showing confirmation page for duplicates: ' + str(duplicates))
          empty_error = (u'<ul class="errorlist"><li>The contacts below have the '
              'same name as contacts you have already entered. Press submit again '
              'to confirm that you want to add them.</li></ul>')
          if est:
            contact_formset = formset_factory(forms.MassDonor)
          else:
            contact_formset = formset_factory(forms.MassDonorPre)
          formset = contact_formset(initial=duplicates)

        else: # saved successfully (no duplicates check needed)
          return HttpResponse("success")

      else: # empty formset
        empty_error = u'<ul class="errorlist"><li>Please enter at least one contact.</li></ul>'

    else: # invalid formset
      logger.info(formset.errors)

    return render(request, 'fund/forms/add_contacts.html', {
      'formset': formset, 'empty_error': empty_error
    })

  else: # GET
    formset = contact_formset()
    steps, news, grants = _get_block_content(membership)
    header = membership.giving_project.title

    return render(request, 'fund/forms/add_contacts.html', {
      '1active': 'true', 'header': header, 'news': news,
      'grants': grants, 'steps': steps, 'formset': formset
    })


@require_member(require_membership=True)
def add_estimates(request):
  membership = request.membership

  initial_form_data = []
  donor_names = [] # to display with forms (which only have pks)

  # get all donors without estimates
  for donor in membership.donor_set.filter(amount__isnull=True):
    initial_form_data.append({'donor': donor})
    donor_names.append(unicode(donor))

  # create formset
  est_formset = formset_factory(forms.DonorEstimates, extra=0)

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
    formset = est_formset(request.POST)
    logger.debug('Adding estimates - posted: ' + str(request.POST))

    if formset.is_valid():
      logger.debug('Adding estimates - is_valid passed, cycling through forms')
      for form in formset.cleaned_data:
        if form:
          donor = form['donor']
          donor.amount = form['amount']
          donor.likelihood = form['likelihood']
          donor.save()
      return HttpResponse("success")

    else: # invalid form
      formset_with_donors = zip(formset, donor_names)
      return render(request, 'fund/forms/add_estimates.html', {
        'formset': formset, 'fd': formset_with_donors
      })

  else: # GET
    formset = est_formset(initial=initial_form_data)
    logger.info('Adding estimates - loading initial formset, size ' +
                 str(len(donor_names)))

    # get vars for base templates
    steps, news, grants = _get_block_content(membership)

    formset_with_donors = zip(formset, donor_names)

    return render(request, 'fund/forms/add_estimates.html', {
      'news': news, 'grants': grants, 'steps': steps,
      '1active': 'true', 'formset': formset, 'fd': formset_with_donors
    })


@require_member(require_membership=True)
def edit_contact(request, donor_id):

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    logger.error('Tried to edit a nonexist donor. User: ' +
                  unicode(request.membership) + ', id given: ' + str(donor_id))
    raise Http404('Donor not found')

  # check whether to require estimates
  est = request.membership.giving_project.require_estimates()

  if request.method == 'POST':
    logger.debug(request.POST)
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    if est:
      form = modelforms.DonorEditForm(request.POST, instance=donor,
                              auto_id=str(donor.pk) + '_id_%s')
    else:
      form = modelforms.DonorPreForm(request.POST, instance=donor,
                                 auto_id=str(donor.pk) + '_id_%s')
    if form.is_valid():
      logger.info('Edit donor success')
      form.save()
      return HttpResponse("success")
  else:
    if est:
      form = modelforms.DonorEditForm(instance=donor, auto_id=str(donor.pk) +
                              '_id_%s')
    else:
      form = modelforms.DonorPreForm(instance=donor, auto_id=str(donor.pk) +
                                 '_id_%s')
  return render(request, 'fund/forms/edit_contact.html',
                {'form': form, 'pk': donor.pk,
                 'action': '/fund/' + str(donor_id) + '/edit'})


@require_member(require_membership=True)
def delete_contact(request, donor_id):

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    logger.warning(str(request.user) + 'tried to delete nonexistent donor: ' +
                    str(donor_id))
    raise Http404('Donor not found')

  action = '/fund/' + str(donor_id) + '/delete'

  if request.method == 'POST':
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    donor.delete()
    return redirect(home)

  return render(request, 'fund/forms/delete_contact.html', {'action': action})

# ----------------------------------------------------------------------------
#  STEPS
# ----------------------------------------------------------------------------

@require_member(require_membership=True)
def add_step(request, donor_id):

  membership = request.membership
  suggested = membership.giving_project.get_suggested_steps()

  logger.info('Single step - start of view. ' + unicode(membership.member) +
               ', donor id: ' + str(donor_id))

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=membership)
  except models.Donor.DoesNotExist:
    logger.error('Single step - tried to add step to nonexistent donor.')
    raise Http404('Donor not found')

  if donor.get_next_step():
    logger.error('Trying to add step, donor has an incomplete')
    return HttpResponse(status=400, content='Donor already has a next step')

  action = '/fund/' + donor_id + '/step'
  formid = 'nextstep-' + donor_id
  divid = donor_id + '-nextstep'

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
    form = modelforms.StepForm(request.POST, auto_id=str(donor.pk) + '_id_%s')
    logger.info('Single step - POST: ' + str(request.POST))
    if form.is_valid():
      step = form.save(commit=False)
      step.donor = donor
      step.save()
      logger.info('Single step - form valid, step saved')
      return HttpResponse("success")
  else:
    form = modelforms.StepForm(auto_id=str(donor.pk) + '_id_%s')

  return render(request, 'fund/forms/add_step.html', {
    'donor': donor, 'form': form, 'action': action, 'divid': divid,
    'formid': formid, 'suggested': suggested,
    'target': str(donor.pk) + '_id_description' # for suggested steps
  })


@require_member(require_membership=True)
def add_mult_step(request):
  initial_form_data = [] # list of dicts for form initial
  donor_list = [] # list of donors for zipping to formset
  size = 0
  membership = request.membership
  suggested = membership.giving_project.get_suggested_steps()

  for donor in membership.donor_set.order_by('-added'):
    if donor.received() == 0 and donor.promised is None and donor.get_next_step() is None:
      initial_form_data.append({'donor': donor})
      donor_list.append(donor)
      size = size + 1
    if size > 9:
      break

  step_formset = formset_factory(forms.MassStep, extra=0)

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
    formset = step_formset(request.POST)
    logger.debug('Multiple steps - posted: ' + str(request.POST))
    if formset.is_valid():
      logger.debug('Multiple steps - is_valid passed, cycling through forms')
      for form in formset.cleaned_data:
        if form:
          step = models.Step(donor=form['donor'], date=form['date'],
                             description=form['description'])
          step.save()
          logger.info('Multiple steps - step created')
      return HttpResponse("success")
    else:
      logger.info('Multiple steps invalid')

  else: # GET
    formset = step_formset(initial=initial_form_data)
    logger.debug('Multiple steps - loading initial formset, size %s', size)

  formset_with_donors = zip(formset, donor_list)

  return render(request, 'fund/forms/add_mult_step.html', {
    'size': size, 'formset': formset, 'fd': formset_with_donors,
    'multi': True, 'suggested': suggested
  })


@require_member(require_membership=True)
def edit_step(request, donor_id, step_id):

  suggested = request.membership.giving_project.get_suggested_steps()

  try:
    donor = models.Donor.objects.get(pk=donor_id,
                                     membership=request.membership)
  except models.Donor.DoesNotExist:
    logger.error(str(request.user) + 'edit step on nonexistent donor ' +
                  str(donor_id))
    raise Http404('Donor not found')

  try:
    step = models.Step.objects.get(id=step_id)
  except models.Step.DoesNotExist:
    logger.error(str(request.user) + 'edit step on nonexistent step ' +
                  str(step_id))
    raise Http404('Step not found')

  action = '/fund/' + str(donor_id) + '/' + str(step_id)
  formid = 'edit-step-' + donor_id
  divid = donor_id + '-nextstep'

  if request.method == 'POST':
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    form = modelforms.StepForm(request.POST, instance=step, auto_id=str(step.pk) +
                           '_id_%s')
    if form.is_valid():
      logger.debug('Edit step success')
      form.save()
      return HttpResponse("success")
  else:
    form = modelforms.StepForm(instance=step, auto_id=str(step.pk) + '_id_%s')

  return render(request, 'fund/forms/edit_step.html', {
    'donor': donor, 'form': form, 'action': action, 'divid': divid,
    'formid': formid, 'suggested': suggested,
    'target': str(step.pk) + '_id_description'
  })


@require_member(require_membership=True)
def complete_step(request, donor_id, step_id):

  membership = request.membership
  suggested = membership.giving_project.get_suggested_steps()

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=membership)
  except models.Donor.DoesNotExist:
    logger.error(str(request.user) + ' complete step on nonexistent donor ' +
                  str(donor_id))
    raise Http404

  try:
    step = models.Step.objects.get(pk=step_id, donor=donor)
  except models.Step.DoesNotExist:
    logger.error(str(request.user) + ' complete step on nonexistent step ' +
                  str(step_id))
    raise Http404

  action = reverse('sjfnw.fund.views.complete_step', kwargs={
    'donor_id': donor_id, 'step_id': step_id
  })

  if request.method == 'POST':
    # update membership activity timestamp
    membership.last_activity = timezone.now()
    membership.save(skip=True)

    # get posted form
    form = forms.StepDoneForm(request.POST, auto_id=str(step.pk) + '_id_%s')
    if form.is_valid():
      logger.info('Completing a step')

      step.completed = timezone.now()
      donor.talked = True
      donor.notes = form.cleaned_data['notes']

      asked = form.cleaned_data['asked']
      response = form.cleaned_data['response']
      promised = form.cleaned_data['promised_amount']
      match_expected = form.cleaned_data['match_expected']
      match_company = form.cleaned_data['match_company']

      # process ask-related input
      if asked:
        if not donor.asked: # asked this step
          logger.debug('Asked this step')
          step.asked = True
          donor.asked = True
        if response == '3': # declined, doesn't matter this step or not
          donor.promised = 0
          step.promised = 0
          logger.debug('Declined')
        if response == '1' and promised and not donor.promised: # pledged this step
          logger.debug('Promise entered')
          step.promised = promised
          donor.promised = promised
          donor.lastname = form.cleaned_data['last_name']
          donor.likely_to_join = form.cleaned_data['likely_to_join']
          logger.info(form.cleaned_data['likely_to_join'])
          donor.promise_reason = json.dumps(form.cleaned_data['promise_reason'])
          logger.info(form.cleaned_data['promise_reason'])
          phone = form.cleaned_data['phone']
          email = form.cleaned_data['email']
          if phone:
            donor.phone = phone
          if email:
            donor.email = email
          if match_expected:
            donor.match_expected = match_expected
            donor.match_company = match_company

      # save donor & completed step
      step.save()
      donor.save()

      # call story creator/updater
      if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine'):
        deferred.defer(membership.update_story, timezone.now())
        logger.info('Calling update story')

      # process next step input
      next_step = form.cleaned_data['next_step']
      next_date = form.cleaned_data['next_step_date']
      if next_step != '' and next_date is not None:
        form2 = modelforms.StepForm().save(commit=False)
        form2.date = next_date
        form2.description = next_step
        form2.donor = donor
        form2.save()
        logger.info('Next step created')

      return HttpResponse('success')
    else: # invalid form
      logger.info('Invalid step completion: ' + str(form.errors))

  else: # GET - fill form with initial data
    initial = {
      'asked': donor.asked, 'notes': donor.notes, 'last_name': donor.lastname,
      'phone': donor.phone, 'email': donor.email,
      'promise_reason': json.loads(donor.promise_reason),
      'likely_to_join': donor.likely_to_join
    }
    if donor.promised:
      if donor.promised == 0:
        initial['response'] = 3
      else:
        initial['response'] = 1
        initial['promised_amount'] = donor.promised
    form = forms.StepDoneForm(auto_id=str(step.pk) + '_id_%s', initial=initial)

  return render(request, 'fund/forms/complete_step.html', {
    'form': form, 'action': action, 'donor': donor, 'suggested': suggested,
    'target': str(step.pk) + '_id_next_step', # for suggested steps
    'step_id': step_id, 'step': step
  })

# ----------------------------------------------------------------------------
#  METHODS USED BY MULTIPLE VIEWS
# ----------------------------------------------------------------------------

def _get_block_content(membership, get_steps=True):
  """ Provide upper block content for the 3 main views

  Args:
    membership: current Membership
    get_steps: whether to include list of upcoming steps

  Returns: Tuple:
    steps: 2 closest upcoming steps (None if get_steps=False)
    news: news items, sorted by date descending
    gp_apps: ProjectApps ordered by org name
  """

  steps, news, gp_apps = None, None, None

  # upcoming steps
  if get_steps:
    steps = (models.Step.objects
        .filter(donor__membership=membership, completed__isnull=True)
        .select_related('donor')
        .order_by('date')[:2])

  # project news
  news = (models.NewsItem.objects
      .filter(membership__giving_project=membership.giving_project)
      .order_by('-date')[:25])

  # grants
  gp_apps = (ProjectApp.objects
      .filter(giving_project=membership.giving_project)
      .exclude(application__pre_screening_status=45) # subcommittee screened out
      .select_related('giving_project', 'application__organization')
      .order_by('application__organization__name'))
  if membership.giving_project.site_visits == 1:
    logger.info('Filtering grants for site visits')
    gp_apps = gp_apps.filter(screening_status__gte=70)

  return steps, news, gp_apps

def _create_membership(member, giving_project, notif=''):
  error = None

  approved = giving_project.is_pre_approved(member.user.username)

  membership, new = models.Membership.objects.get_or_create(
      member=member, giving_project=giving_project,
      defaults={'approved': approved, 'notifications': notif})

  if not new:
    error = 'You are already registered with that giving project.'
  else:
    member.current = membership.pk
    member.save()

  return membership, error
