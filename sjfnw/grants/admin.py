import logging

from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.safestring import mark_safe

from sjfnw import utils
from sjfnw.admin import BaseModelAdmin, BaseShowInline, YearFilter
from sjfnw.grants import models, modelforms

logger = logging.getLogger('sjfnw')

# Note: some non-standard fields have been added in order to add text to templates
# from a centralized location:
#  - list_help_text: display help text at top of changelist page
#  - list_action_link: display link at top of changelist page
# see sjfnw/templates/admin/change_list.html

LOG_IN_AS_ORG = utils.create_link(
  '/admin/grants/organization/login', # reverse crashes, don't know why
  'Log in as an organization',
  new_tab=True
)
# -----------------------------------------------------------------------------
#  CUSTOM FILTERS
# -----------------------------------------------------------------------------

class GPGYearFilter(YearFilter):
  filter_model = models.GivingProjectGrant
  field = 'created'

class ReportYearFilter(YearFilter):
  filter_model = models.GranteeReport
  field = 'created'

class GrantApplicationYearFilter(YearFilter):
  filter_model = models.GrantApplication
  field = 'submission_time'

  def lookups(self, request, model_admin):
    return [(y, y) for y in range(2013, timezone.now().date().year + 1)]

class CycleTypeFilter(admin.SimpleListFilter):
  title = 'Grant cycle type'
  parameter_name = 'cycle_type'

  def __init__(self, req, params, model, model_admin):
    self.model = model
    super(CycleTypeFilter, self).__init__(req, params, model, model_admin)

  def lookups(self, request, model_admin):
    cycle_types = [
      'Criminal Justice',
      'Economic Justice',
      'Environmental Justice',
      'Gender Justice',
      'General',
      'Immigration',
      'Momentum',
      'Montana',
      'Rapid Response',
      'Rural Justice',
      'Seed',
    ]
    return [(t, t) for t in cycle_types]

  def queryset(self, request, queryset):
    if not self.value():
      return queryset
    elif self.model == models.GrantCycle:
      return queryset.filter(title__startswith=self.value())
    elif self.model == models.GrantApplication:
      return queryset.filter(
        grant_cycle__title__startswith=self.value())
    elif self.model == models.GivingProjectGrant:
      return queryset.filter(
        projectapp__application__grant_cycle__title__startswith=self.value())
    elif self.model == models.GranteeReport:
      return queryset.filter(
        giving_project_grant__projectapp__application__grant_cycle__title__startswith=self.value())

class CycleOpenFilter(admin.SimpleListFilter):
  title = 'Cycle status'
  parameter_name = 'status'

  def lookups(self, request, model_admin):
    return (
      (None, 'Open & upcoming (default)'),
      ('open', 'Open'),
      ('upcoming', 'Upcoming'),
      ('closed', 'Closed'),
      ('all', 'All')
    )

  def choices(self, cl):
    for lookup, title in self.lookup_choices:
      yield {
        'selected': self.value() == lookup,
        'query_string': cl.get_query_string({self.parameter_name: lookup}, []),
        'display': title,
      }

  def queryset(self, request, queryset):
    if self.value() == 'all':
      return queryset
    now = timezone.now()
    if self.value() == 'open':
      return queryset.filter(open__lte=now, close__gt=now)
    elif self.value() == 'upcoming':
      return queryset.filter(open__gt=now)
    elif self.value() == 'closed':
      return queryset.filter(close__lt=now)

    return queryset.filter(close__gt=now)

class IsArchivedFilter(admin.SimpleListFilter):
  title = 'Archived'
  parameter_name = 'archived'

  def lookups(self, request, model_admin):
    return (
      (None, 'False (default)'),
      ('true', 'True'),
      ('all', 'All')
    )

  def choices(self, cl):
    for lookup, title in self.lookup_choices:
      yield {
        'selected': self.value() == lookup,
        'query_string': cl.get_query_string({self.parameter_name: lookup,}, []),
        'display': title,
      }

  def queryset(self, request, queryset):
    if self.value() == 'all':
      return queryset
    if self.value() == 'true':
      return queryset.filter(archived__isnull=False)
    return queryset.filter(archived__isnull=True)


class MultiYearGrantFilter(admin.SimpleListFilter):
  title = 'Grant length'
  parameter_name = 'multiyear'

  def lookups(self, request, model_admin):
    return [
      (1, 'Single-year'),
      (2, 'Two-year')
    ]

  def queryset(self, request, queryset):
    if self.value() == '1':
      return queryset.filter(second_amount__isnull=True)
    if self.value() == '2':
      return queryset.filter(second_amount__isnull=False)
    return queryset

class OrgRegisteredFilter(admin.SimpleListFilter):
  title = 'Registered'
  parameter_name = 'registered'

  def lookups(self, request, model_admin):
    return [
      (1, 'Yes'),
      (0, 'No')
    ]

  def queryset(self, request, queryset):
    if self.value() == '1':
      return queryset.filter(user__isnull=False)
    elif self.value() == '0':
      return queryset.filter(user__isnull=True)
    return queryset

# -----------------------------------------------------------------------------
#  INLINES
# -----------------------------------------------------------------------------

class LogReadonlyI(admin.TabularInline):
  """ Show existing logs as an inline. Can be deleted but not edited.
      Used by Org, Application """
  model = models.GrantApplicationLog
  extra = 0
  max_num = 0
  fields = ['date', 'grantcycle', 'staff', 'contacted', 'notes']
  readonly_fields = ['date', 'grantcycle', 'staff', 'contacted', 'notes']
  verbose_name = 'Log'
  verbose_name_plural = 'Logs'
  collapsed = True
  show_change_link = True

  def get_queryset(self, request):
    qs = super(LogReadonlyI, self).get_queryset(request)
    return qs.select_related('staff', 'application', 'application__grant_cycle')

  def grantcycle(self, obj):
    if obj.application:
      return obj.application.grant_cycle
    else:
      return ''
  grantcycle.short_description = 'Application' # app is identified by grant cycle in this case


class LogI(admin.TabularInline):
  """ Inline for adding a log to an org or application
      Shows one blank row. Autofills org or app depending on current page """
  model = models.GrantApplicationLog
  extra = 1
  max_num = 1
  can_delete = False
  exclude = ['date'] # auto-populated
  verbose_name_plural = 'Add a log entry'

  def get_queryset(self, request):
    return models.GrantApplicationLog.objects.none()

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    """ Give initial values for staff and/or org.
        This is called once on every foreign key field """
    if '/add' not in request.path: # skip when creating new org/app
      # autofill staff field
      if db_field.name == 'staff':
        kwargs['initial'] = request.user.id
        kwargs['queryset'] = User.objects.filter(is_staff=True)
        return db_field.formfield(**kwargs)

      # organization field on app page
      elif 'grantapplication' in request.path and db_field.name == 'organization':
        app_id = int(request.path.split('/')[-2])
        app = models.GrantApplication.objects.get(pk=app_id)
        kwargs['initial'] = app.organization_id
        kwargs['queryset'] = models.Organization.objects.filter(pk=app.organization_id)
        return db_field.formfield(**kwargs)

      # application field
      if db_field.name == 'application':
        org_pk = int(request.path.split('/')[-2])
        kwargs['queryset'] = (models.GrantApplication.objects
            .select_related('organization', 'grant_cycle')
            .filter(organization_id=org_pk))

    return super(LogI, self).formfield_for_foreignkey(db_field, request, **kwargs)


class AppCycleI(BaseShowInline):
  """ List related applications on a cycle page """
  model = models.GrantApplication
  readonly_fields = ['organization', 'submission_time', 'pre_screening_status']
  fields = ['organization', 'submission_time', 'pre_screening_status']
  show_change_link = True
  change_link_text = "View/edit"


class CycleReportQuestionI(admin.TabularInline):
  model = models.CycleReportQuestion
  fields = ('order', 'report_question', 'required')
  extra = 0
  collapsed = True

class CycleNarrativeI(admin.TabularInline):
  model = models.CycleNarrative
  fields = ('order', 'narrative_question')
  extra = 0
  formset = modelforms.CycleNarrativeFormset
  collapsed = True

  def formfield_for_manytomany(self, db_field, request, **kwargs):
    kwargs['queryset'] = models.CycleNarrative.objects.filter(archived__isnull=True)
    return super(CycleNarrativeI, self).formfield_for_manytomany(db_field, request, **kwargs)


class GrantApplicationI(BaseShowInline):
  """ List grant applications on organization page """
  model = models.GrantApplication
  readonly_fields = ('submission_time', 'grant_cycle', 'summary', 'read')
  fields = ('submission_time', 'grant_cycle', 'summary', 'read')
  show_change_link = True
  change_link_text = "View/edit"

  def get_queryset(self, request):
    return super(GrantApplicationI, self).get_queryset(request).select_related('grant_cycle')

  def summary(self, obj):
    """ Display a summary of screening status, giving projects, and awards """

    summary = ''

    if obj.pk:
      summary += obj.get_pre_screening_status_display() + '. '

      projectapps = obj.projectapp_set.all().select_related('giving_project', 'givingprojectgrant')
      for papp in projectapps:
        summary += unicode(papp.giving_project)
        if papp.get_screening_status_display():
          summary += '. ' + papp.get_screening_status_display()
        if hasattr(papp, 'givingprojectgrant'):
          summary += ': ${:,}'.format(int(papp.givingprojectgrant.total_amount()))
        summary += '.\n'

    return summary

  def read(self, obj):
    return utils.create_link('/grants/view/{}'.format(obj.pk), 'Read application', new_tab=True)
  read.allow_tags = True


class SponsoredProgramI(BaseShowInline):
  """ List sponsored program grants on organization page """
  model = models.SponsoredProgramGrant
  fields = ['amount', 'check_mailed', 'approved']
  readonly_fields = fields
  template = 'admin/grants/sponsoredprogramgrant/tabular.html'
  show_change_link = True
  change_link_text = "View/edit"


class ProjectAppI(admin.TabularInline):
  """ Display giving projects assigned to this app """
  model = models.ProjectApp
  extra = 1
  fields = ['giving_project', 'screening_status', 'granted', 'grantee_report']
  readonly_fields = ['granted', 'grantee_report']
  verbose_name = 'Giving project'
  verbose_name_plural = 'Giving projects'

  def granted(self, obj):
    """ For existing projectapps, shows grant amount or link to add a grant """
    if obj.pk:
      link = '<a target="_blank" href="/admin/grants/givingprojectgrant/'
      if hasattr(obj, 'givingprojectgrant'):
        award = obj.givingprojectgrant
        link += '{}/">${:,}</a>'
        if obj.givingprojectgrant.grant_length() > 1:
          link += ' (' + str(obj.givingprojectgrant.grant_length()) + '-year)'
        return mark_safe(link.format(award.pk, award.total_amount()))
      else:
        link = link + 'add/?projectapp={}">Enter an award</a>'
        return mark_safe(link.format(obj.pk))
    return ''

  def grantee_report(self, obj):
    if obj.pk:
      reports = (models.GranteeReport.objects
          .select_related('giving_project_grant')
          .filter(giving_project_grant__projectapp_id=obj.pk))
      report_link = ""
      for i, report in enumerate(reports):
        if i > 0:
          report_link += " | "
        report_link += utils.create_link('/admin/grants/granteereport/{}/'.format(report.pk),
                                      'Year {}'.format(i + 1), new_tab=True)
      return mark_safe(report_link)
    else:
      return ''

# -----------------------------------------------------------------------------
#  MODELADMIN
# -----------------------------------------------------------------------------

class GrantCycleA(BaseModelAdmin):
  list_display = ['title', 'open', 'close']
  list_filter = (CycleOpenFilter, CycleTypeFilter)
  fieldsets = (
    ('', {
      'fields': (
        ('title', 'private'),
        ('open', 'close'),
        ('info_page', 'amount_note'),
        ('email_signature', 'conflicts'),
      )
    }),
    # Hack - 'collapse' class makes django admin's collapse.js load
    # which supports custom 'collapsed' option for inlines
    ('', {'classes': ('collapse',), 'fields': ()})
  )
  inlines = [CycleNarrativeI, CycleReportQuestionI, AppCycleI]

class GranteeReportA(BaseModelAdmin):
  list_display = (
    'giving_project_grant',
    'organization',
    'created',
    'giving_project',
    'grant_cycle',
    'view_link'
  )
  list_filter = (ReportYearFilter, CycleTypeFilter)
  search_fields = (
    'giving_project_grant__projectapp__application__organization__name',
    'giving_project_grant__projectapp__giving_project',
  )
  fields = ('grant_display', 'created', 'view_link')
  readonly_fields = ('grant_display', 'created', 'view_link')

  def get_queryset(self, request):
    qs = super(GranteeReportA, self).get_queryset(request)
    return qs.select_related(
      'giving_project_grant__projectapp__application__grant_cycle',
      'giving_project_grant__projectapp__application__organization',
      'giving_project_grant__projectapp__giving_project'
    )

  def has_add_permission(self, request):
    return False

  def organization(self, obj):
    return obj.giving_project_grant.projectapp.application.organization

  def giving_project(self, obj):
    return obj.giving_project_grant.projectapp.giving_project

  def grant_cycle(self, obj):
    return obj.giving_project_grant.projectapp.application.grant_cycle

  def grant_display(self, obj):
    return utils.create_link(
      reverse('admin:grants_givingprojectgrant_change', args=(obj.giving_project_grant_id,)),
      unicode(obj.giving_project_grant)
    )
  grant_display.allow_tags = True
  grant_display.short_description = 'Giving project grant'

  def view_link(self, obj):
    if obj.pk:
      url = reverse('sjfnw.grants.views.view_grantee_report', kwargs={'report_id': obj.pk})
      return utils.create_link(url, 'View report', new_tab=True)
  view_link.allow_tags = True
  view_link.short_description = 'View'

class ReportQuestionA(BaseModelAdmin):
  list_display = ('name', 'version', 'input_type', 'word_limit', 'archived_display')
  list_filter = (IsArchivedFilter, 'name', 'version')
  search_fields = ('name', 'version')
  fields = ('name', 'version', 'input_type', 'text', 'word_limit', 'archived')

  # TODO replace/remove in django 1.9
  # https://docs.djangoproject.com/en/1.9/releases/1.9/#django-contrib-admin
  def archived_display(self, obj):
    return obj.archived or ''
  archived_display.short_description = 'Archived'

class NarrativeQuestionA(BaseModelAdmin):
  list_display = ('question', 'version', 'word_limit_display', 'archived_display')
  list_filter = (IsArchivedFilter, 'name', 'version')
  search_fields = ('name', 'version')
  form = modelforms.NarrativeQuestionForm
  fields = ('name', 'version', 'text', 'word_limit', 'archived')

  # TODO replace/remove in django 1.9
  # https://docs.djangoproject.com/en/1.9/releases/1.9/#django-contrib-admin
  def archived_display(self, obj):
    return obj.archived or ''
  archived_display.short_description = 'Archived'

  def question(self, obj):
    return obj.display_name()

  def word_limit_display(self, obj):
    return (obj.word_limit or '<b>Unlimited</b>') if obj.uses_word_limit() else '-'
  word_limit_display.short_description = 'Word limit'
  word_limit_display.allow_tags = True


class OrganizationA(BaseModelAdmin):
  list_display = ['name', 'user']
  list_action_link = LOG_IN_AS_ORG
  search_fields = ['name', 'user__username']
  list_filter = (OrgRegisteredFilter,)

  fieldsets = [
      ('', {
        'fields': (('name', 'user'),)
      }),
      ('Staff-entered contact info', {
        'fields': (('staff_contact_person', 'staff_contact_person_title',
                    'staff_contact_phone', 'staff_contact_email'),)
      }),
      ('Contact info from most recent application', {
        'fields': (
          ('address', 'city', 'state', 'zip'),
          ('contact_person', 'contact_person_title', 'telephone_number', 'email_address'),
          ('fax_number', 'website')
        )
      }),
      ('Organization info from most recent application', {
        'fields': (('founded', 'status', 'ein', 'mission'),)
      }),
      ('Fiscal sponsor info from most recent application', {
        'classes': ('collapse',),
        'fields': (
          ('fiscal_org', 'fiscal_person'),
          ('fiscal_telephone', 'fiscal_address', 'fiscal_email')
        )
      })
    ]

  def change_view(self, request, object_id, form_url='', extra_context=None):
    self.inlines = [GrantApplicationI, SponsoredProgramI, LogReadonlyI, LogI]
    self.readonly_fields = [
      'address', 'city', 'state', 'zip', 'telephone_number',
      'fax_number', 'email_address', 'website', 'status', 'ein', 'founded',
      'mission', 'fiscal_org', 'fiscal_person', 'fiscal_telephone',
      'fiscal_address', 'fiscal_email', 'fiscal_letter', 'contact_person',
      'contact_person_title'
    ]
    return super(OrganizationA, self).change_view(request, object_id)

  def get_actions(self, request):
    return {
      'merge': (OrganizationA.merge, 'merge', 'Merge')
    }

  def merge(self, request, queryset):
    if len(queryset) == 2:
      return redirect(reverse(
        'sjfnw.grants.views.merge_orgs',
        kwargs={'id_a': queryset[0].pk, 'id_b': queryset[1].pk}
      ))
    messages.warning(request,
      'Merge can only be done on two organizations. You selected {}.'.format(len(queryset)))


class GrantApplicationA(BaseModelAdmin):
  list_display = ['organization', 'grant_cycle', 'submission_time', 'read']
  list_filter = (GrantApplicationYearFilter, 'pre_screening_status', CycleTypeFilter)
  list_action_link = utils.create_link('/admin/grants/search', 'Run a report', new_tab=True)
  search_fields = ['organization__name', 'grant_cycle__title']
  ordering = ('-submission_time',)

  fieldsets = [
    ('Application', {
        'fields': (('organization_link', 'grant_cycle', 'submission_time',
                   'read'),)
    }),
    ('Application contact info', {
        'classes': ('collapse',),
        'description':
            ('Contact information as entered in the grant application. '
              'You may edit this as needed.  Note that the contact information '
              'you see on the organization page is always from the most recent '
              'application, whether that is this or a different one.'),
        'fields': (('address', 'city', 'state', 'zip', 'telephone_number',
                     'fax_number', 'email_address', 'website'),
                   ('status', 'ein'))
    }),
    ('Uploaded files', {
        'classes': ('collapse',),
        'fields': ('get_files_display',)
    }),
    ('Administration', {
      'fields': (
        ('pre_screening_status', 'scoring_bonus_poc', 'scoring_bonus_geo', 'site_visit_report'),
        ('revert_grant', 'rollover')
      )
    })
  ]
  readonly_fields = ('organization_link', 'grant_cycle', 'submission_time',
                     'read', 'revert_grant', 'rollover', 'get_files_display')
  inlines = [ProjectAppI, LogReadonlyI, LogI]

  def get_files_display(self, obj):
    files = ''

    for field_name in models.GrantApplication.file_fields():
      # attribute is a FieldFile instance if set
      field_file = getattr(obj, field_name) if hasattr(obj, field_name) else None

      if field_file:
        url = reverse('sjfnw.grants.views.view_file', kwargs={
          'obj_type': 'app', 'obj_id': obj.pk, 'field_name': field_name
        })

        file_link = utils.create_link(url, obj.get_file_name(field_name), new_tab=True)

        # to get the human-readable field name, we need to access the FileField
        verbose_name = obj._meta.get_field(field_name).verbose_name

        files += '<tr><td>{}</td><td>{}</td></tr>'.format(verbose_name, file_link)

    return '<table>' + (files or 'No files uploaded') + '</table>'

  get_files_display.allow_tags = True
  get_files_display.short_description = 'Uploaded files'

  def has_add_permission(self, request):
    return False

  def revert_grant(self, _):
    return utils.create_link('revert', 'Revert to draft')
  revert_grant.allow_tags = True

  def rollover(self, _):
    return utils.create_link('rollover', 'Copy to another grant cycle')
  rollover.allow_tags = True

  def organization_link(self, obj):
    return utils.create_link('/admin/grants/organization/{}/'.format(obj.organization.pk),
                             unicode(obj.organization))
  organization_link.allow_tags = True
  organization_link.short_description = 'Organization'

  def read(self, obj):
    return utils.create_link('/grants/view/{}'.format(obj.pk), 'Read application', new_tab=True)
  read.allow_tags = True


class DraftGrantApplicationA(BaseModelAdmin):
  list_display = ['organization', 'grant_cycle', 'modified', 'overdue',
                  'extended_deadline']
  list_filter = ['grant_cycle']
  list_action_link = LOG_IN_AS_ORG
  fields = [('organization', 'grant_cycle', 'modified'),
            ('extended_deadline'),
            ('edit')]
  readonly_fields = ['modified', 'edit']
  form = modelforms.DraftAdminForm
  search_fields = ['organization__name']

  def get_readonly_fields(self, request, obj=None):
    if obj is not None: # editing - lock org & cycle
      return self.readonly_fields + ['organization', 'grant_cycle']
    return self.readonly_fields

  def edit(self, obj):
    if not obj or not obj.organization:
      return '-'
    url = reverse('sjfnw.grants.views.grant_application',
                  kwargs={'cycle_id': obj.grant_cycle_id})
    url += '?user=' + obj.organization.get_email()
    return (utils.create_link(url, "Edit this draft", new_tab=True) +
            '<br>(logs you in as the organization)')
  edit.allow_tags = True


class GivingProjectGrantA(BaseModelAdmin):
  list_display = (
    'organization_name', 'grant_cycle', 'giving_project',
    'short_created', 'total_grant', 'fully_paid', 'check_mailed'
  )
  search_fields = (
    'projectapp__application__organization__name',
    'projectapp__giving_project__title'
  )
  list_filter = [CycleTypeFilter, GPGYearFilter, MultiYearGrantFilter]
  list_select_related = True

  list_help_text = (
    '<p>To enter a new grant, Find the corresponding <a href="/admin/grants/grantapplication/">grant application</a> and use the "Enter an award" link.  This page is for viewing and updating awards.</p>'
  )

  fieldsets = (
    ('', {
      'classes': ('wide',),
      'fields': (
        ('projectapp', 'created'),
        ('total_grant',),
        ('amount',), 
        ('check_number', 'check_mailed'),
        ('agreement_mailed', 'agreement_returned'),
        'approved'
      )
    }),
    ('Grantee report', {
      'classes': ('wide',),
      'fields': (('first_report_due', 'second_report_due'),),
    }),
    ('Multi-Year Grant', {
      'classes': ('wide',),
      'fields': (('second_amount', 'second_check_number', 'second_check_mailed'),)
    })
  )
  readonly_fields = ['created', 'total_grant']

  # overrides - change view only

  def get_formsets_with_inlines(self, request, obj=None):
    # django-recommended way to hide an inline on change page
    # https://docs.djangoproject.com/en/1.8/ref/contrib/admin/#django.contrib.admin.ModelAdmin.get_formsets_with_inlines
    for inline in self.get_inline_instances(request, obj):
      if obj is None:
        continue
      yield inline.get_formset(request, obj), inline

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    """ Restrict db query to selected projectapp if specified in url """
    logger.info('gpg page formfield_for_foreignkey')
    if db_field.name == 'projectapp':
      p_app = request.GET.get('projectapp')
      if p_app:
        kwargs['queryset'] = (models.ProjectApp.objects
            .select_related('application', 'application__organization', 'giving_project')
            .filter(pk=p_app))
        logger.info('grant page loaded with projectapp specified ' + p_app)
    return super(GivingProjectGrantA, self).formfield_for_foreignkey(
        db_field, request, **kwargs)

  def get_readonly_fields(self, request, obj=None):
    """ Don't allow projectapp to be changed once the grant has been created """
    if obj is not None:
      self.readonly_fields.append('projectapp')
    return self.readonly_fields

  # custom methods - list and change views

  def total_grant(self, obj):
    if obj:
      amt = obj.total_amount()
      if amt:
        return '${:,}'.format(amt)
    return '-'
  total_grant.short_description = 'Total grant amount (Updates on save)'

  # custom methods - list only

  def fully_paid(self, obj):
    return obj.fully_paid()
  fully_paid.boolean = True

  def giving_project(self, obj):
    return unicode(obj.projectapp.giving_project)
  giving_project.admin_order_field = 'projectapp__giving_project__title'

  def grant_cycle(self, obj):
    return unicode(obj.projectapp.application.grant_cycle.title)
  grant_cycle.admin_order_field = 'projectapp__application__grant_cycle__title'

  def organization_name(self, obj):
    return obj.projectapp.application.organization.name
  organization_name.admin_order_field = 'projectapp__application__organization__name'

  def short_created(self, obj):
    return obj.created.strftime('%m/%d/%y')
  short_created.short_description = 'Created'
  short_created.admin_order_field = 'created'


class SponsoredProgramGrantA(BaseModelAdmin):
  list_display = ['organization', 'amount', 'check_mailed']
  list_filter = ['check_mailed']
  exclude = ['entered']
  fields = [('organization', 'amount'),
            ('check_number', 'check_mailed', 'approved'),
            'description']

  def get_readonly_fields(self, request, obj=None):
    if obj is not None:
      return self.readonly_fields + ('organization',)
    return self.readonly_fields

class GranteeReportDraftA(BaseModelAdmin):
  list_display = (
    'giving_project_grant',
    'organization',
    'giving_project',
    'grant_cycle',
    'modified',
    'due'
  )

  fields = (('organization', 'grant'),
            ('modified', 'due'),
            ('giving_project', 'grant_cycle'))
  readonly_fields = ('organization', 'modified', 'due', 'giving_project',
    'grant', 'grant_cycle')

  def get_queryset(self, request):
    qs = super(GranteeReportDraftA, self).get_queryset(request)
    return qs.select_related(
      'giving_project_grant__projectapp__application__grant_cycle',
      'giving_project_grant__projectapp__application__organization',
      'giving_project_grant__projectapp__giving_project'
    )

  def has_add_permission(self, request):
    return False

  def organization(self, obj):
    return obj.giving_project_grant.projectapp.application.organization

  def giving_project(self, obj):
    return obj.giving_project_grant.projectapp.giving_project

  def grant_cycle(self, obj):
    return obj.giving_project_grant.projectapp.application.grant_cycle

  def grant(self, obj):
    return utils.create_link(
      reverse('admin:grants_givingprojectgrant_change', args=(obj.giving_project_grant_id,)),
      'View'
    )
  grant.allow_tags = True

  def due(self, obj):
    return obj.giving_project_grant.next_report_due()


class LogA(BaseModelAdmin):
  form = modelforms.LogAdminForm
  fields = (('organization', 'date'),
            'staff',
            'application',
            ('contacted'),
            'notes')
  readonly_fields = ['organization']
  list_display = ['date', 'organization', 'application', 'staff']

  def get_model_perms(self, *args, **kwargs):
    perms = super(LogA, self).get_model_perms(*args, **kwargs)
    perms['unlisted'] = True
    return perms

class NarrativeAnswerA(BaseModelAdmin):
  fields = (
    ('organization', 'question', 'grant_cycle'),
    'answer'
  )
  readonly_fields = ('organization', 'question', 'grant_cycle', 'answer')
  list_display = (
    'question',
    'organization',
    'grant_cycle'
  )
  search_fields = (
    'cycle_narrative__narrative_question__name',
    'cycle_narrative__narrative_question__version',
    'grant_application__organization__name',
    'grant_application__grant_cycle__title'
  )

  def get_queryset(self, request):
    qs = super(NarrativeAnswerA, self).get_queryset(request)
    return qs.select_related(
      'cycle_narrative__narrative_question',
      'grant_application__organization',
      'grant_application__grant_cycle'
    )

  def answer(self, obj):
    return obj.get_display_value()
  answer.allow_tags = True

  def question(self, obj):
    return obj.cycle_narrative.narrative_question

  def organization(self, obj):
    return obj.grant_application.organization

  def grant_cycle(self, obj):
    return obj.grant_application.grant_cycle

# -----------------------------------------------------------------------------
#  REGISTER
# -----------------------------------------------------------------------------

admin.site.register(models.NarrativeAnswer, NarrativeAnswerA)
admin.site.register(models.GrantCycle, GrantCycleA)
admin.site.register(models.NarrativeQuestion, NarrativeQuestionA)
admin.site.register(models.Organization, OrganizationA)
admin.site.register(models.GrantApplication, GrantApplicationA)
admin.site.register(models.DraftGrantApplication, DraftGrantApplicationA)
admin.site.register(models.GivingProjectGrant, GivingProjectGrantA)
admin.site.register(models.SponsoredProgramGrant, SponsoredProgramGrantA)
admin.site.register(models.GrantApplicationLog, LogA)
admin.site.register(models.ReportQuestion, ReportQuestionA)
admin.site.register(models.GranteeReportDraft, GranteeReportDraftA)
admin.site.register(models.GranteeReport, GranteeReportA)
