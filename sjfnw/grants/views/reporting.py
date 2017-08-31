import logging

from sjfnw.grants.forms.admin import (AppReportForm, GPGrantReportForm,
    OrgReportForm, SponsoredAwardReportForm)

logger = logging.getLogger('sjfnw')

def grants_report(request):
  """ Handles grant reporting

    Displays all reporting forms
    Uses report-type-specific methods to handle POSTs
  """

  app_form = AppReportForm()
  org_form = OrgReportForm()
  gp_grant_form = GPGrantReportForm()
  sponsored_form = SponsoredAwardReportForm()

  context = {
    'app_form': app_form,
    'org_form': org_form,
    'gp_grant_form': gp_grant_form,
    'sponsored_form': sponsored_form
  }

  if request.method == 'POST':
    # Determine type of report
    if 'run-application' in request.POST:
      logger.info('App report')
      form = AppReportForm(request.POST)
      context['app_form'] = form
      context['active_form'] = '#application-form'
      results_func = get_app_results

    elif 'run-organization' in request.POST:
      logger.info('Org report')
      form = OrgReportForm(request.POST)
      context['org_form'] = form
      context['active_form'] = '#organization-form'
      results_func = get_org_results

    elif 'run-giving-project-grant' in request.POST:
      logger.info('Giving project grant report')
      form = GPGrantReportForm(request.POST)
      context['award_form'] = form
      context['active_form'] = '#giving-project-grant-form'
      results_func = get_gpg_results

    elif 'run-sponsored-award' in request.POST:
      logger.info('Sponsored award report')
      form = SponsoredAwardReportForm(request.POST)
      context['award_form'] = form
      context['active_form'] = '#sponsored-award-form'
      results_func = get_sponsored_award_results

    else:
      logger.error('Unknown report type')
      form = None

    if form and form.is_valid():
      options = form.cleaned_data
      logger.info('A valid form: ' + str(options))

      # get results
      field_names, results = results_func(options)

      # format results
      if options['format'] == 'browse':
        return render_to_response('grants/report_results.html',
                                  {'results': results, 'field_names': field_names})
      elif options['format'] == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % 'grantapplications'
        writer = unicodecsv.writer(response)
        writer.writerow(field_names)
        for row in results:
          writer.writerow(row)
        return response
    else:
      logger.warning('Invalid form!')

  # human-friendly lists of always-included fields
  context['app_base'] = 'submission time, organization name, grant cycle'
  context['gpg_base'] = ('date check was mailed, amount (total and by year), '
                         'organization, giving project, grant cycle')
  context['sponsored_base'] = 'date check was mailed, amount, organization'
  context['org_base'] = 'name'
  return render(request, 'grants/reporting.html', context)

def get_min_max_year(options):
  current_tz = timezone.get_current_timezone()
  min_year = datetime.strptime(options['year_min'], '%Y') # will default to beginning of year
  min_year = timezone.make_aware(min_year, current_tz)
  max_year = datetime.strptime(options['year_max'] + '-12-31 23:59:59', '%Y-%m-%d %H:%M:%S')
  max_year = timezone.make_aware(max_year, current_tz)
  return min_year, max_year

def get_app_results(options):
  """ Fetches application report results

  Arguments:
    options - cleaned_data from a request.POST-filled instance of AppReportForm

  Returns:
    A list of display-formatted field names. Example:
      ['Submitted', 'Organization', 'Grant cycle']

    A list of applications & related info. Example:
      [
        ['2011-04-20 06:18:36+0:00', 'Justice League', 'LGBTQ Grant Cycle'],
        ['2013-10-23 09:08:56+0:00', 'ACLU of Idaho', 'General Grant Cycle'],
      ]
  """
  logger.info('Get app results')

  apps = models.GrantApplication.objects.order_by('-submission_time').select_related(
      'organization', 'grant_cycle')

  # filters
  min_year, max_year = get_min_max_year(options)
  apps = apps.filter(submission_time__gte=min_year, submission_time__lte=max_year)

  if options.get('organization_name'):
    apps = apps.filter(organization__name__contains=options['organization_name'])
  if options.get('city'):
    apps = apps.filter(city=options['city'])
  if options.get('state'):
    apps = apps.filter(state__in=options['state'])
  if options.get('has_fiscal_sponsor'):
    apps = apps.exclude(fiscal_org='')

  if options.get('pre_screening_status'):
    apps = apps.filter(pre_screening_status__in=options.get('pre_screening_status'))
  if options.get('screening_status'):
    apps = apps.filter(projectapp__screening_status__in=options.get('screening_status'))
  if options.get('poc_bonus'):
    apps = apps.filter(scoring_bonus_poc=True)
  if options.get('geo_bonus'):
    apps = apps.filter(scoring_bonus_geo=True)
  if options.get('grant_cycle'):
    apps = apps.filter(grant_cycle__title__in=options.get('grant_cycle'))
  if options.get('giving_projects'):
    apps = apps.prefetch_related('giving_projects')
    apps = apps.filter(giving_projects__title__in=options.get('giving_projects'))

  # fields
  fields = (['submission_time', 'organization', 'grant_cycle'] +
            options['report_basics'] + options['report_contact'] +
            options['report_org'] + options['report_proposal'] +
            options['report_budget'])
  if options['report_fiscal']:
    fields += models.GrantApplication.fields_starting_with('fiscal')
    fields.remove('fiscal_letter')
  # TODO re-implement references reporting
  if options['report_bonuses']:
    fields.append('scoring_bonus_poc')
    fields.append('scoring_bonus_geo')

  # format headers
  field_names = [f.capitalize().replace('_', ' ') for f in fields]

  # gp screening, grant awards
  get_gps = False
  get_gp_ss = False
  get_awards = False
  if options['report_gps']:
    field_names.append('Assigned GPs')
    get_gps = True
  if options['report_gp_screening']:
    field_names.append('GP screening status')
    get_gp_ss = True
  if options['report_award']:
    field_names.append('Awarded')
    get_awards = True

  # execute queryset, populate results
  results = []
  for app in apps:
    row = []

    # application fields
    for field in fields:
      if field == 'pre_screening_status':
        # convert screening status to human-readable version
        val = getattr(app, field)
        if val:
          convert = dict(gc.PRE_SCREENING)
          val = convert[val]
        row.append(val)
      elif field == 'submission_time':
        row.append(local_date_str(getattr(app, field)))
      else:
        row.append(getattr(app, field))

    # gp GPs, screening status, awards
    if get_gps or get_awards or get_gp_ss:
      award_col = ''
      ss_col = ''
      gp_col = ''
      papps = app.projectapp_set.all()
      if papps:
        for papp in papps:
          if get_gps:
            if gp_col != '':
              gp_col += ', '
            gp_col += '%s' % papp.giving_project.title
          if get_awards:
            try:
              award = papp.givingprojectgrant
              if award_col != '':
                award_col += ', '
              award_col += '%s %s ' % (award.total_amount(), papp.giving_project.title)
            except models.GivingProjectGrant.DoesNotExist:
              pass
          if get_gp_ss:
            if ss_col != '':
              ss_col += ', '
            if papp.screening_status:
              ss_col += '%s (%s) ' % (dict(gc.SCREENING)[papp.screening_status],
                papp.giving_project.title)
            else:
              ss_col += '%s (none) ' % papp.giving_project.title
      if get_gps:
        row.append(gp_col)
      if get_gp_ss:
        row.append(ss_col)
      if get_awards:
        row.append(award_col)

    results.append(row)

  return field_names, results

def get_org_results(options):
  """ Fetch organization report results

  Args:
    options: cleaned_data from a request.POST-filled instance of OrgReportForm

  Returns:
    A list of display-formatted field names. Example:
      ['Name', 'Login', 'State']

    A list of organization & related info. Each item is a list of requested values
    Example: [
        ['Fancy pants org', 'fancy@pants.org', 'ID'],
        ['Justice League', 'trouble@gender.org', 'WA']
      ]
  """

  # initial queryset
  orgs = models.Organization.objects.all()

  # filters
  reg = options.get('registered')
  if reg is True:
    orgs = orgs.exclude(user__isnull=True)
  elif reg is False:
    org = orgs.filter(user__isnull=True)
  if options.get('organization_name'):
    orgs = orgs.filter(name__contains=options['organization_name'])
  if options.get('city'):
    orgs = orgs.filter(city=options['city'])
  if options.get('state'):
    orgs = orgs.filter(state__in=options['state'])
  if options.get('has_fiscal_sponsor'):
    orgs = orgs.exclude(fiscal_org='')

  # fields
  fields = ['name']
  if options.get('report_account_email'):
    fields.append('email')
  fields += options['report_contact'] + options['report_org']
  if options.get('report_fiscal'):
    fields += models.GrantApplication.fields_starting_with('fiscal')
    fields.remove('fiscal_letter')

  field_names = [f.capitalize().replace('_', ' ') for f in fields] # for display

  # related objects
  get_apps = False
  get_awards = False
  if options.get('report_applications'):
    get_apps = True
    orgs = orgs.prefetch_related('grantapplication_set')
    field_names.append('Grant applications')
  if options.get('report_awards'):
    orgs = orgs.prefetch_related('grantapplication_set')
    orgs = orgs.prefetch_related('sponsoredprogramgrant_set')
    field_names.append('Grants awarded')
    get_awards = True

  # execute queryset, build results
  results = []
  linebreak = '\n' if options['format'] == 'csv' else '<br>'
  for org in orgs:
    row = []

    # org fields
    for field in fields:
      if field == 'email':
        row.append(org.get_email())
      else:
        row.append(getattr(org, field))

    awards_str = ''
    if get_apps or get_awards:
      apps_str = ''

      for app in org.grantapplication_set.all():
        if get_apps:
          apps_str += (app.grant_cycle.title + ' ' +
            app.submission_time.strftime('%m/%d/%Y') + linebreak)

        # giving project grants
        if get_awards:
          for papp in app.projectapp_set.all():
            try:
              award = papp.givingprojectgrant
              timestamp = award.check_mailed or award.created
              if timestamp:
                timestamp = timestamp.strftime('%m/%d/%Y')
              else:
                timestamp = 'No timestamp'
              awards_str += u'${} {} {}{}'.format(award.total_amount(),
                award.projectapp.giving_project.title, timestamp, linebreak)
            except models.GivingProjectGrant.DoesNotExist:
              pass

      if get_apps:
        row.append(apps_str)

    # sponsored program grants
    if get_awards:
      for award in org.sponsoredprogramgrant_set.all():
        awards_str += '$%s %s %s' % (award.amount, ' sponsored program grant ',
            (award.check_mailed or award.entered).strftime('%m/%d/%Y'))
        awards_str += linebreak
      row.append(awards_str)

    results.append(row)

  return field_names, results

def get_gpg_results(options):
  """ Fetch giving project grant report results

  Args:
    options: cleaned_data from a request.POST-filled instance of AwardReportForm

  Returns:
    field_names: A list of display-formatted field names.
      Example: ['Amount', 'Check mailed', 'Organization']

    results: A list of requested values for each award.
      Example (matching field_names example): [
          ['10000', '2013-10-23 09:08:56+0:00', 'Fancy pants org'],
          ['5987', '2011-08-04 09:08:56+0:00', 'Justice League']
        ]
  """

  # initial queryset
  gp_awards = models.GivingProjectGrant.objects.select_related(
      'projectapp__application__organization', 'projectapp__giving_project')

  # filters
  min_year, max_year = get_min_max_year(options)
  gp_awards = gp_awards.filter(created__gte=min_year, created__lte=max_year)

  if options.get('organization_name'):
    gp_awards = gp_awards.filter(
        projectapp__application__organization__name__contains=options['organization_name'])

  if options.get('city'):
    gp_awards = gp_awards.filter(projectapp__application__city=options['city'])

  if options.get('state'):
    gp_awards = gp_awards.filter(projectapp__application__state__in=options['state'])

  if options.get('has_fiscal_sponsor'):
    gp_awards = gp_awards.exclude(projectapp__application__fiscal_org='')

  if options.get('grant_cycle'):
    gp_awards = gp_awards.filter(
      projectapp__application__grant_cycle__title__in=options.get('grant_cycle')
    )
  if options.get('giving_projects'):
    gp_awards = gp_awards.filter(
      projectapp__giving_project__title__in=options.get('giving_projects')
    )

  # fields
  fields = ['check_mailed', 'first_year_amount', 'second_year_amount', 'total_amount',
            'organization', 'giving_project', 'grant_cycle']

  if options.get('report_id'):
    fields.append('id')
  if options.get('report_check_number'):
    fields.append('check_number')
  if options.get('report_date_approved'):
    fields.append('approved')
  if options.get('report_agreement_dates'):
    fields.append('agreement_mailed')
    fields.append('agreement_returned')
  if options.get('report_year_end_report_due'):
    fields.append('year_end_report_due')
  if options.get('report_support_type'):
    fields.append('support_type')

  org_fields = options['report_contact'] + options['report_org']
  if options.get('report_fiscal'):
    org_fields += models.GrantApplication.fields_starting_with('fiscal')
    org_fields.remove('fiscal_letter')

  # get values
  results = []
  for award in gp_awards:
    row = []
    for field in fields:
      if field == 'organization':
        row.append(award.projectapp.application.organization.name)
      elif field == 'grant_cycle':
        row.append(award.projectapp.application.grant_cycle.title)
      elif field == 'support_type':
        row.append(award.projectapp.application.support_type)
      elif field == 'giving_project':
        row.append(award.projectapp.giving_project.title)
      elif field == 'year_end_report_due':
        row.append(award.next_yer_due())
      elif field == 'first_year_amount':
        row.append(award.amount)
      elif field == 'second_year_amount':
        row.append(award.second_amount or '')
      elif field == 'total_amount':
        row.append(award.total_amount())
      else:
        row.append(getattr(award, field, ''))
    for field in org_fields:
      row.append(getattr(award.projectapp.application.organization, field))
    results.append(row)

  field_names = [f.capitalize().replace('_', ' ') for f in fields]
  field_names += ['Org. ' + f.capitalize().replace('_', ' ') for f in org_fields]

  return field_names, results

def get_sponsored_award_results(options):
  sponsored = models.SponsoredProgramGrant.objects.select_related('organization')

  min_year, max_year = get_min_max_year(options)
  sponsored = sponsored.filter(entered__gte=min_year, entered__lte=max_year)

  if options.get('organization_name'):
    sponsored = sponsored.filter(organization__name__contains=options['organization_name'])
  if options.get('city'):
    sponsored = sponsored.filter(organization__city=options['city'])
  if options.get('state'):
    sponsored = sponsored.filter(organization__state__in=options['state'])
  if options.get('has_fiscal_sponsor'):
    sponsored = sponsored.exclude(organization__fiscal_org='')

  # fields
  fields = ['check_mailed', 'amount', 'organization']
  if options.get('report_id'):
    fields.append('id')
  if options.get('report_check_number'):
    fields.append('check_number')
  if options.get('report_date_approved'):
    fields.append('approved')

  org_fields = options['report_contact'] + options['report_org']
  if options.get('report_fiscal'):
    org_fields += models.GrantApplication.fields_starting_with('fiscal')
    org_fields.remove('fiscal_letter')

  # get values
  results = []
  for award in sponsored:
    row = []
    for field in fields:
      if hasattr(award, field):
        row.append(getattr(award, field))
      else:
        row.append('')
    for field in org_fields:
      row.append(getattr(award.organization, field))
    results.append(row)

  field_names = [f.capitalize().replace('_', ' ') for f in fields]
  field_names += ['Org. ' + f.capitalize().replace('_', ' ') for f in org_fields]

  return field_names, results
