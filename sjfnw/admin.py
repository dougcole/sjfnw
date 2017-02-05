import logging

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User

from sjfnw.fund.models import Member
from sjfnw.grants.models import Organization

logger = logging.getLogger('sjfnw')

# Shared admin classes
# ---------------------

class BaseModelAdmin(admin.ModelAdmin):
  """ Base class for setting a universal per-page limit """
  list_per_page = 30


class BaseShowInline(admin.TabularInline):
  """ Base inline for read only items """
  extra = 0
  max_num = 0
  can_delete = False


class YearFilter(admin.SimpleListFilter):
  """ Base filter by year. Usage: create a child class and override the class variables:

    Required override:
      filter_model: the model that has the date field to use for filtering

    Optional overrides:
      intermediate: string that connects the model being filtered to the filter_model
                    (required if the model being filtered != the filter_model)
      title: displayed in filters sidebar (default: 'year')
      parameter_name: query parameter name (default: 'year')
  """
  title = 'year'
  parameter_name = 'year'
  filter_model = None
  field = ''
  intermediate = ''

  def lookups(self, request, model_admin):
    dates = (self.filter_model.objects
        .values_list(self.field, flat=True)
        .order_by('-%s' % self.field))
    prev = None
    years = []
    for date in dates:
      if date.year != prev:
        years.append((date.year, date.year))
        prev = date.year
    return years

  def queryset(self, request, queryset):
    val = self.value()
    if not val:
      return queryset
    try:
      year = int(val)
    except ValueError:
      logger.error('YearFilter received invalid value %s', val)
      messages.error(request,
          'Error loading filter. Contact techsupport@socialjusticefund.org')
      return queryset
    else:
      filt = {}
      key = self.intermediate + '__' if self.intermediate else ''
      filt['{}{}__year'.format(key, self.field)] = year
      return queryset.filter(**filt)

# Configure admin site
# ---------------------

admin.site.index_template = 'admin/index_custom.html'
admin.site.site_header = 'Social Justice Fund NW Admin Site'
admin.site.site_title = 'SJF Admin'
admin.site.index_title = None

admin.site.unregister(Group)
admin.site.unregister(User)

class MemberI(BaseShowInline):
  model = Member
  fields = ('first_name', 'last_name')
  readonly_fields = ('first_name', 'last_name')
  show_change_link = True

class UserA(UserAdmin):
  """ Customized ModelAdmin using django's UserAdmin as base"""
  list_display = ('username', 'is_superuser')
  search_fields = ('username',)
  fieldsets = (
      (None, {
        'fields': (
          ('username', 'password'),
          ('date_joined', 'last_login')
        )
      }),
      ('Permissions', {
        'fields': ('is_active', 'is_staff', 'is_superuser')
      })
  )
  readonly_fields = ['last_login', 'date_joined']

  inlines = (MemberI,)

admin.site.register(User, UserA)
