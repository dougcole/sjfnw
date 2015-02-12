import datetime, logging, json

from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
from django.utils import timezone
from django.utils.safestring import mark_safe

from libs import unicodecsv

from sjfnw.admin import advanced_admin
from sjfnw.fund.models import *
from sjfnw.fund import forms, utils, modelforms
from sjfnw.grants.models import ProjectApp, GrantApplication

logger = logging.getLogger('sjfnw')

# display methods
def step_membership(obj): #Step list_display
  return obj.donor.membership

def gp_year(obj): #GP list_display
  year = obj.fundraising_deadline.year
  if year == timezone.now().year:
    return '<b>%d</b>' % year
  else:
    return year
gp_year.short_description = 'Year'
gp_year.allow_tags = True


def ship_progress(obj):
  p = obj.get_progress()
  # TODO use string formatting with dict
  return ('<table><tr><td style="width:25%;padding:1px;">$' +
          str(p['estimated']) + '</td><td style="width:25%;padding:1px;">$' +
          str(p['promised']) + '</td><td style="width:25%;padding:1px;">$' +
          str(p['received_total']) + '</td><td style="width:25%;padding:1px">' +
          str(p['received_this']) + ', ' + str(p['received_next']) +
          ', ' + str(p['received_afternext']) + '</td></tr></table>')
ship_progress.short_description = 'Estimated, promised, received, rec. by year'
ship_progress.allow_tags = True


# Filters
class PromisedBooleanFilter(SimpleListFilter): #donors & steps
  title = 'promised'
  parameter_name = 'promised_tf'

  def lookups(self, request, model_admin):
    return (('True', 'Promised'), ('False', 'Declined'),
              ('None', 'None entered'))

  def queryset(self, request, queryset):
    if self.value() == 'True':
      return queryset.filter(promised__gt=0)
    if self.value() == 'False':
      return queryset.filter(promised=0)
    elif self.value() == 'None':
      return queryset.filter(promised__isnull=True)

class ReceivedBooleanFilter(SimpleListFilter): #donors & steps
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


class GPYearFilter(SimpleListFilter):
  """ Filter giving projects by year """
  title = 'year'
  parameter_name = 'year'

  def lookups(self, request, model_admin):
    deadlines = GivingProject.objects.values_list(
        'fundraising_deadline', flat=True
        ).order_by('-fundraising_deadline')
    prev = None
    years = []
    for deadline in deadlines:
      if deadline.year != prev:
        years.append((deadline.year, deadline.year))
        prev = deadline.year
    logger.info(years)
    return years

  def queryset(self, request, queryset):
    val = self.value()
    if not val:
      return queryset
    try:
      year = int(val)
    except:
      logger.error('GPYearFilter received invalid value %s', val)
      messages.error(request,
          'Error loading filter. Contact techsupport@socialjusticefund.org')
      return queryset
    return queryset.filter(fundraising_deadline__year=year)


# Inlines
class MembershipInline(admin.TabularInline): #GP
  model = Membership
  formset = forms.MembershipInlineFormset
  extra = 0
  can_delete = False
  fields = ('member', 'giving_project', 'approved', 'leader',)

  def formfield_for_foreignkey(self, db_field, request, **kwargs):

    # cache member choices to reduce queries
    if db_field.name == 'member':

      cached_choices = getattr(request, 'cached_members', None)
      if cached_choices:
        logger.debug('Using cached choices for membership inline')
        formfield = super(MembershipInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        formfield.choices = cached_choices

      else:
        members = Member.objects.all()
        formfield = super(MembershipInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        formfield.choices = [(member.pk, unicode(member)) for member in members]
        request.cached_members = formfield.choices

      return formfield

    else: # different field
      return super(MembershipInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class ProjectResourcesInline(admin.TabularInline): #GP
  model = ProjectResource
  extra = 0
  template = 'admin/fund/tabular_projectresource.html'
  fields = ('resource', 'session',)

class DonorInline(admin.TabularInline): #membership
  model = Donor
  extra = 0
  max_num = 0
  can_delete = False
  readonly_fields = ('firstname', 'lastname', 'amount', 'talked', 'asked',
                     'promised')
  fields = ('firstname', 'lastname', 'amount', 'talked', 'asked', 'promised')

class ProjectAppInline(admin.TabularInline):
  model = ProjectApp
  extra = 1
  verbose_name = 'Grant application'
  verbose_name_plural = 'Grant applications'
  raw_id_fields = ('giving_project',)

  #def get_queryset(self, request):
  #  qs = super(ProjectAppInline, self).get_queryset(request)
  #  return qs.select_related('application')

  def formfield_for_foreignkey(self, db_field, request, **kwargs):

    # cache application choices to reduce queries
    if db_field.name == 'application':

      cached_choices = getattr(request, 'cached_projectapps', None)
      if cached_choices:
        logger.debug('Using cached choices for projectapp inline')
        formfield = super(ProjectAppInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        formfield.choices = cached_choices

      else:
        apps = GrantApplication.objects.select_related('grant_cycle', 'organization')
        try:
          gp_id = int(request.path.split('/')[-2])
        except:
          logger.info('Could not parse gp id, not limiting app choices')
        else:
          gp = GivingProject.objects.get(pk=gp_id)
          year = gp.fundraising_deadline - datetime.timedelta(weeks=52)
          apps = apps.filter(submission_time__gte=year)
        finally:
          formfield = super(ProjectAppInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
          # create choices from queryset (doing manually results in less queries)
          formfield.choices = [('', '---------')] + [(app.pk, unicode(app)) for app in apps]
          request.cached_projectapps = formfield.choices
          logger.debug('Cached app choices for projectapp inline')

      return formfield

    else: #other field
      return super(ProjectAppInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class SurveyI(admin.TabularInline):

  model = GPSurvey
  extra = 1
  verbose_name = 'Survey'
  verbose_name_plural = 'Surveys'

# ModelAdmin
class GivingProjectA(admin.ModelAdmin):
  list_display = ('title', gp_year, 'estimated')
  list_filter = (GPYearFilter,)
  readonly_fields = ('estimated',)
  fields = (('title', 'public'),
            ('fundraising_training', 'fundraising_deadline'),
            'fund_goal', 'site_visits', 'calendar', 'suggested_steps', 'pre_approved')
  form = modelforms.GivingProjectAdminForm
  inlines = [SurveyI, ProjectResourcesInline, MembershipInline, ProjectAppInline]

class MemberAdvanced(admin.ModelAdmin): #advanced only
  list_display = ('first_name', 'last_name', 'email')
  search_fields = ['first_name', 'last_name', 'email']

class MembershipA(admin.ModelAdmin):

  #list_select_related = True
  actions = ['approve']
  list_display = ('member', 'giving_project', ship_progress, 'overdue_steps',
                  'last_activity', 'approved', 'leader')
  list_filter = ('approved', 'leader', 'giving_project') #add overdue steps
  search_fields = ['member__first_name', 'member__last_name']
  readonly_list = (ship_progress, 'overdue_steps',)

  fields = (('member', 'giving_project', 'approved'),
      ('leader', 'last_activity', 'emailed'),
      (ship_progress),
      'notifications'
  )
  readonly_fields = ('last_activity', 'emailed', ship_progress)
  inlines = [DonorInline]

  def approve(self, request, queryset): #Membership action
    logger.info('Approval button pressed; looking through queryset')
    for memship in queryset:
      if memship.approved == False:
        utils.NotifyApproval(memship)
    queryset.update(approved=True)
    logger.info('Approval queryset updated')


class DonorA(admin.ModelAdmin):
  list_display = ('firstname', 'lastname', 'membership', 'amount', 'talked', 'asked',
                  'promised', 'received_this', 'received_next', 'received_afternext')
  list_filter = ('membership__giving_project', 'asked', PromisedBooleanFilter,
                 ReceivedBooleanFilter)
  list_editable = ('received_this', 'received_next', 'received_afternext')
  search_fields = ['firstname', 'lastname', 'membership__member__first_name',
                   'membership__member__last_name']
  actions = ['export_donors']

  fields = ('membership',
            ('firstname', 'lastname'),
            ('phone', 'email'),
            ('amount', 'likelihood'),
            ('talked', 'asked', 'promised', 'promise_reason_display', 'likely_to_join'),
            ('received_this', 'received_next', 'received_afternext'),
            'notes')

  readonly_fields = ('promise_reason_display', 'likely_to_join')

  def export_donors(self, request, queryset):
    logger.info('Export donors called by ' + request.user.email)

    response = HttpResponse(mimetype='text/csv')
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
                year, donor.received_this, year+1, donor.received_next, year+2,
                donor.received_afternext, donor.notes,
                donor.get_likely_to_join_display(),
                donor.promise_reason_display()]
      writer.writerow(fields)
      count += 1
    logger.info(str(count) + ' donors exported')
    return response


class NewsA(admin.ModelAdmin):
  list_display = ('summary', 'date', 'membership')
  list_filter = ('membership__giving_project',)

class StepAdv(admin.ModelAdmin): #adv only
  list_display = ('description', 'donor', step_membership, 'date', 'completed',
                  'promised')
  list_filter = ('donor__membership', PromisedBooleanFilter,
                 ReceivedBooleanFilter)

class SurveyA(admin.ModelAdmin):
  list_display = ('title', 'updated')
  readonly_fields = ('updated',)
  form = modelforms.CreateSurvey
  fields = ('title', 'intro', 'questions')

  def save_model(self, request, obj, form, change):
    obj.updated = timezone.now()
    obj.updated_by = request.user.username
    obj.save()

class SurveyResponseA(admin.ModelAdmin):
  list_display = ('gp_survey', 'date')
  list_filter = ('gp_survey__giving_project',)
  fields = ('gp_survey', 'date', 'display_responses')
  readonly_fields = ('gp_survey', 'date', 'display_responses')
  actions = ['export_responses']

  def display_responses(self, obj):
    if obj and obj.responses:
      resp_list = json.loads(obj.responses)
      disp = '<table><tr><th>Question</th><th>Answer</th></tr>'
      for i in range(0, len(resp_list), 2):
        disp += ('<tr><td>' + unicode(resp_list[i]) + '</td><td>' +
                 unicode(resp_list[i+1]) + '</td></tr>')
      disp += '</table>'
      return mark_safe(disp)
  display_responses.short_description = 'Responses'

  def export_responses(self, request, queryset):

    logger.info('Export survey responses called by ' + request.user.email)
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=survey_responses %s.csv' % (timezone.now().strftime('%Y-%m-%d'),)
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
        fields.append(responses[i+1])
        questions = max(questions, (i+2)/2)
      response_rows.append(fields)

    logger.info('Max %d questions', questions)
    for i in range(0, questions):
      header.append('Question')
      header.append('Answer')
    writer.writerow(header)
    for row in response_rows:
      writer.writerow(row)

    return response

admin.site.register(GivingProject, GivingProjectA)
admin.site.register(Membership, MembershipA)
admin.site.register(NewsItem, NewsA)
admin.site.register(Donor, DonorA)
admin.site.register(Resource)
admin.site.register(Survey, SurveyA)
admin.site.register(SurveyResponse, SurveyResponseA)

advanced_admin.register(Member, MemberAdvanced)
advanced_admin.register(Donor, DonorA)
advanced_admin.register(Membership, MembershipA)
advanced_admin.register(GivingProject, GivingProjectA)
advanced_admin.register(NewsItem, NewsA)
advanced_admin.register(Step, StepAdv)
advanced_admin.register(ProjectResource)
advanced_admin.register(Resource)

