import datetime, logging, json

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.utils import timezone
from django.utils.safestring import mark_safe

import unicodecsv

from sjfnw import utils
from sjfnw.admin import BaseModelAdmin, BaseShowInline, YearFilter
from sjfnw.fund.models import (GivingProject, Member, Membership, Survey,
    GPSurvey, Resource, ProjectResource, Donor, NewsItem, SurveyResponse)
from sjfnw.fund import forms, modelforms, utils as fund_utils
from sjfnw.grants.models import ProjectApp, GrantApplication

logger = logging.getLogger('sjfnw')

# -----------------------------------------------------------------------------
#  Filters
# -----------------------------------------------------------------------------

class PromisedFilter(SimpleListFilter):
  """ Filter by promised field """

  title = 'promised'
  parameter_name = 'promised'

  def lookups(self, request, model_admin):
    return (('True', 'Promised'),
            ('False', 'Declined'),
            ('Unknown', 'No response entered'))

  def queryset(self, request, queryset):
    if self.value() == 'True':
      return queryset.filter(promised__gt=0)
    if self.value() == 'False':
      return queryset.filter(promised=0)
    elif self.value() == 'Unknown':
      return queryset.filter(promised__isnull=True)


class ReceivedBooleanFilter(SimpleListFilter):
  """ Filter by received (any of received_this, _next, _afternext) """
  title = 'received'
  parameter_name = 'received_tf'

  def lookups(self, request, model_admin):
    return (('True', 'Gift received'), ('False', 'No gift received'))

  def queryset(self, request, queryset):
    if self.value() == 'True':
      return queryset.exclude(
          received_this=0, received_next=0, received_afternext=0)
    if self.value() == 'False':
      return queryset.filter(
          received_this=0, received_next=0, received_afternext=0)


class GPYearFilter(YearFilter):
  filter_model = GivingProject
  field = 'fundraising_deadline'


class DonorLikelyToJoinFilter(SimpleListFilter):
  title = 'likely to join'
  parameter_name = 'ltj'

  def lookups(self, request, model_admin):
    return ((3, '3 - Definitely'),
            (2, '2 - Likely'),
            (1, '1 - Unlikely'),
            (0, '0 - No chance'),
            ('positive', 'Likely or definitely'),
            ('none', 'No answer'))

  def queryset(self, request, queryset):
    val = self.value()
    if val == 'positive':
      return queryset.filter(likely_to_join__gt=1)
    elif val == 'none':
      return queryset.filter(likely_to_join__isnull=True)
    elif val:
      return queryset.filter(likely_to_join=val)

# -----------------------------------------------------------------------------
# Inlines
# -----------------------------------------------------------------------------

class MembershipInline(admin.TabularInline):
  model = Membership
  formset = forms.MembershipInlineFormset
  extra = 0
  fields = ['member', 'giving_project', 'approved', 'leader']
  show_change_link = True

  def formfield_for_foreignkey(self, db_field, request, **kwargs):

    # cache member choices to reduce queries
    if db_field.name == 'member':

      cached_choices = getattr(request, 'cached_members', None)
      if cached_choices:
        logger.debug('Using cached choices for membership inline')
        formfield = super(MembershipInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs)
        formfield.choices = cached_choices

      else:
        members = Member.objects.all()
        formfield = super(MembershipInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs)
        formfield.choices = [(member.pk, unicode(member)) for member in members]
        request.cached_members = formfield.choices

      return formfield

    else: # different field
      return super(MembershipInline, self).formfield_for_foreignkey(
          db_field, request, **kwargs)


class ProjectResourcesInline(admin.TabularInline):
  model = ProjectResource
  extra = 0
  fields = ['resource', 'session']
  help_text = ('Resources are grouped by session when displayed to the '
    'user, with sessions listed alphabetically.')


class DonorInline(BaseShowInline):
  model = Donor
  readonly_fields = ('firstname', 'lastname', 'amount', 'talked', 'asked',
      'promised')
  fields = ('firstname', 'lastname', 'amount', 'talked', 'asked', 'promised')
  show_change_link = True


class ProjectAppInline(admin.TabularInline):
  model = ProjectApp
  extra = 1
  verbose_name = 'Grant application'
  verbose_name_plural = 'Grant applications'
  fields = ['application', 'app_link', 'screening_status', 'grant_link']
  readonly_fields = ['app_link', 'grant_link']
  ordering = ['screening_status']

  def get_queryset(self, request):
    return super(ProjectAppInline, self).get_queryset(request).select_related(
        'application', 'givingprojectgrant')

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    """ Limit application choices to those submitted no more than 1 year before
        giving project's fundrasing deadline

        For performance and to avoid a 'response too large' error
    """
    formfield = super(ProjectAppInline, self).formfield_for_foreignkey(
        db_field, request, **kwargs)

    if db_field.name == 'application' and request.resolver_match.args:
      apps = GrantApplication.objects.select_related('grant_cycle', 'organization')
      try:
        gp_id = int(request.resolver_match.args[0])
      except ValueError:
        # shoudn't be possible, but catch it in case
        logger.error('Could not parse GP id. URL: %s, ResolverMatch args: %s',
                     request.path, request.resolver_match.args)
      else:
        gp = GivingProject.objects.get(pk=gp_id)
        year = gp.fundraising_deadline - datetime.timedelta(weeks=52)
        apps = apps.filter(submission_time__gte=year)
        formfield.choices = [('', '---------')] + [(app.pk, unicode(app)) for app in apps]

    return formfield

  def app_link(self, obj):
    if obj and hasattr(obj, 'application'):
      return utils.create_link(
        reverse('admin:grants_grantapplication_change', args=(obj.application.pk,)),
        'View application')
    else:
      return ''

  def grant_link(self, obj):
    if obj:
      if hasattr(obj, 'givingprojectgrant'):
        return utils.create_link(
          reverse('admin:grants_givingprojectgrant_change', args=(obj.givingprojectgrant.pk,)),
          'View grant')

      if hasattr(obj, 'screening_status') and obj.screening_status > 80:
        return utils.create_link(
          '{}?projectapp={}'.format(reverse('admin:grants_givingprojectgrant_add'), obj.pk),
          'Add grant')
    else:
      return ''


class GPSurveyI(admin.TabularInline):
  model = GPSurvey
  extra = 1
  verbose_name = 'Survey'
  verbose_name_plural = 'Surveys'

  def get_queryset(self, request):
    return super(GPSurveyI, self).get_queryset(request).select_related('survey')

# -----------------------------------------------------------------------------
# ModelAdmin
# -----------------------------------------------------------------------------

@admin.register(GivingProject)
class GivingProjectA(BaseModelAdmin):
  list_per_page = 15
  list_display = ['title', 'gp_year', 'estimated']
  list_filter = [GPYearFilter]

  fields = [
    ('title', 'public'),
    ('fundraising_training', 'fundraising_deadline'),
    'fund_goal', 'site_visits', 'calendar', 'suggested_steps', 'pre_approved'
  ]
  readonly_fields = ['estimated']
  form = modelforms.GivingProjectAdminForm
  inlines = [MembershipInline]

  def change_view(self, request, object_id, form_url='', extra_context=None):
    self.inlines = [MembershipInline, GPSurveyI, ProjectResourcesInline, ProjectAppInline]
    return super(GivingProjectA, self).change_view(
      request, object_id, form_url=form_url, extra_context=extra_context
    )

  def gp_year(self, obj):
    year = obj.fundraising_deadline.year
    if year == timezone.now().year:
      return mark_safe('<b>%d</b>' % year)
    else:
      return year
  gp_year.short_description = 'Year'


@admin.register(Resource)
class ResourceA(BaseModelAdmin):
  list_display = ['title', 'created']
  list_help_text = '<p>NOTE: This page is for viewing all of the resources that have been stored.  To add resources to a giving project, edit that project and use the Project Resources section at the bottom.</p>'
  fields = ['title', 'summary', 'link']


@admin.register(Member)
class MemberA(BaseModelAdmin):
  list_display = ['first_name', 'last_name', 'user']
  search_fields = ['first_name', 'last_name', 'user__username']

  fields = (('first_name', 'last_name', 'user'),)
  inlines = (MembershipInline,)


@admin.register(Membership)
class MembershipA(BaseModelAdmin):
  actions = ['approve']
  search_fields = ['member__first_name', 'member__last_name']
  list_display = ['member', 'giving_project', 'list_progress', 'overdue_steps',
                  'last_activity', 'approved', 'leader']
  list_filter = ['approved', 'leader', 'giving_project']
  readonly_list = ['list_progress', 'overdue_steps']
  list_select_related = ['member', 'giving_project']

  fields = [('member', 'giving_project', 'approved'),
            ('leader',),
            ('last_activity', 'emailed'),
            ('progress'),
            'notifications']
  readonly_fields = ['last_activity', 'emailed', 'progress']
  inlines = [DonorInline]
  ordering = ['-last_activity']

  def get_queryset(self, request):
    return super(MembershipA, self).get_queryset(request).prefetch_related('donor_set')

  def approve(self, _, queryset):
    for memship in queryset:
      if memship.approved is False:
        fund_utils.notify_approval(memship)
    queryset.update(approved=True)

  def list_progress(self, obj): # for membership list - mimics columns
    membership_progress = obj.get_progress()
    return mark_safe((
      '<table class="nested-column nested-column-4"><tr><td>${estimated}</td>'
      '<td>${promised}</td><td>${received_total}</td>'
      '<td>{received_this}, {received_next}, {received_afternext}</td>'
      '</tr></table>').format(**membership_progress)
    )
  list_progress.short_description = mark_safe(
      '<table class="nested-column-4"><tr><td>Estimated</td><td>Total promised</td>'
      '<td>Received</td><td>Rec. by year</td></tr></table>')

  def progress(self, obj): # for single membership view
    membership_progress = obj.get_progress()
    year = obj.giving_project.fundraising_deadline.year
    return mark_safe((
        'Estimated: ${estimated}<br>Promised: ${promised}<br>'
        'Received: ${received_total}<br>Received by year: {year}: ${received_this} / '
        '{next}: ${received_next} / {after_next}: ${received_afternext}'
      ).format(year=year, next=year + 1, after_next=year + 2, **membership_progress))


@admin.register(Donor)
class DonorA(BaseModelAdmin):
  actions = ['export_donors']
  search_fields = ['firstname', 'lastname', 'membership__member__first_name',
                   'membership__member__last_name']
  list_display = ['firstname', 'lastname', 'membership', 'amount', 'talked',
                  'asked', 'total_promised', 'received_this', 'received_next',
                  'received_afternext', 'match_expected', 'match_received']
  list_editable = ['received_this', 'received_next', 'received_afternext',
                   'match_expected', 'match_received']
  list_filter = ['asked', PromisedFilter, ReceivedBooleanFilter, DonorLikelyToJoinFilter,
                 'membership__giving_project']
  list_select_related = ['membership__giving_project', 'membership__member']
  list_help_text = (
    '<p>The years in the "Received" columns are relative to the year listed in the "Membership" column. When exporting donor data, the years for each amount will be listed explicitly.</p>'
    '<p>Enter received numbers as dollar amounts without commas. (I.e. 5000 not <i>5,000</i> or <i>5000.00</i>)</p>'
  )
  fields = [
    'membership',
    ('firstname', 'lastname'),
    ('phone', 'email'),
    ('amount', 'likelihood'),
    ('talked', 'asked', 'promised', 'promise_reason_display', 'likely_to_join'),
    ('received_this', 'received_next', 'received_afternext'),
    ('match_expected', 'match_company', 'match_received'),
    'notes'
  ]
  readonly_fields = ['promise_reason_display', 'likely_to_join']

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    field = super(DonorA, self).formfield_for_foreignkey(db_field, request, **kwargs)
    if db_field.name == 'membership':
      ships = Membership.objects.select_related('giving_project', 'member')
      field.choices = [(ship.pk, unicode(ship)) for ship in ships]
    return field

  def export_donors(self, request, queryset):
    logger.info('Export donors called by %s', request.user.username)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=prospects.csv'
    writer = unicodecsv.writer(response)

    writer.writerow(['First name', 'Last name', 'Phone', 'Email', 'Member',
                     'Giving Project', 'Amount to ask', 'Asked', 'Promised',
                     'Received - TOTAL', 'Received - Year', 'Received - Amount',
                     'Received - Year', 'Received - Amount',
                     'Received - Year', 'Received - Amount', 'Notes',
                     'Likelihood of joining a GP', 'Reasons for donating'])
    count = 0
    for donor in queryset:
      year = donor.membership.giving_project.fundraising_deadline.year
      fields = [donor.firstname, donor.lastname, donor.phone, donor.email,
                donor.membership.member, donor.membership.giving_project,
                donor.amount, donor.asked, donor.promised, donor.received(),
                year, donor.received_this, year + 1, donor.received_next, year + 2,
                donor.received_afternext, donor.notes,
                donor.get_likely_to_join_display(),
                donor.promise_reason_display(), donor.total_promised(),
                donor.match_expected, donor.match_received, donor.match_company]
      writer.writerow(fields)
      count += 1
    logger.info(str(count) + ' donors exported')
    return response


@admin.register(NewsItem)
class NewsA(BaseModelAdmin):
  list_display = ['summary', 'date', 'membership']
  list_filter = ['membership__giving_project']


@admin.register(Survey)
class SurveyA(BaseModelAdmin):
  list_display = ['title', 'updated']
  form = modelforms.CreateSurvey
  fields = ['title', 'intro', 'questions']
  readonly_fields = ['updated']

  def save_model(self, request, obj, form, change):
    obj.updated = timezone.now()
    obj.updated_by = request.user.username
    obj.save()


@admin.register(SurveyResponse)
class SurveyResponseA(BaseModelAdmin):
  search_fields = ['gp_survey__survey__title', 'gp_survey__giving_project__title']
  list_display = ['gp_survey', 'date']
  list_filter = ['date', 'gp_survey__giving_project']

  fields = ['gp_survey', 'date', 'display_responses']
  readonly_fields = ['gp_survey', 'date', 'display_responses']
  actions = ['export_responses']

  def display_responses(self, obj):
    if obj and obj.responses:
      resp_list = json.loads(obj.responses)
      disp = '<table><tr><th>Question</th><th>Answer</th></tr>'
      for i in range(0, len(resp_list), 2):
        disp += ('<tr><td>' + unicode(resp_list[i]) + '</td><td>' +
                 unicode(resp_list[i + 1]) + '</td></tr>')
      disp += '</table>'
      return mark_safe(disp)
  display_responses.short_description = 'Responses'

  def export_responses(self, request, queryset):

    logger.info('Export survey responses called by ' + request.user.username)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename=survey_responses %s.csv'
        % timezone.now().strftime('%Y-%m-%d'))
    writer = unicodecsv.writer(response)

    header = ['Date', 'Survey ID', 'Giving Project', 'Survey'] # base
    questions = 0
    response_rows = []
    for survey in queryset:
      fields = [survey.date, survey.gp_survey_id,
                survey.gp_survey.giving_project.title,
                survey.gp_survey.survey.title]
      logger.info(isinstance(survey.responses, str))
      responses = json.loads(survey.responses)
      for i in range(0, len(responses), 2):
        fields.append(responses[i])
        fields.append(responses[i + 1])
        questions = max(questions, (i + 2) / 2)
      response_rows.append(fields)

    logger.info('Max %d questions', questions)
    for i in range(0, questions):
      header.append('Question')
      header.append('Answer')
    writer.writerow(header)
    for row in response_rows:
      writer.writerow(row)

    return response
