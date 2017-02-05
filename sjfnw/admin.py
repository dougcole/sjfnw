import logging

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse

from sjfnw import utils
from sjfnw.fund.models import Member
from sjfnw.grants.models import Organization

logger = logging.getLogger('sjfnw')

# Shared admin classes
# ---------------------

class BaseModelAdmin(admin.ModelAdmin):
  """ Provide baseline per-page limit to reduce page load times """
  list_per_page = 30


class BaseShowInline(admin.TabularInline):
  """ For read only items """
  extra = 0
  max_num = 0
  can_delete = False


class YearFilter(admin.SimpleListFilter):
  """ Filter results by the year on the given date field.

    Date field does not have to be on the model being filtered
    To use, create a child class and override the class variables below.
  """
  filter_model = None   # model being filtered
  field = ''            # name of date field used to filter
  intermediate = ''     # string path to the model that 'field' is on - if not filter_model

  title = 'year'
  parameter_name = 'year'

  def lookups(self, request, model_admin):
    """ Returns an array of year values found in existing data """
    dates = (self.filter_model.objects.values_list(self.field, flat=True)
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

class UserA(UserAdmin):
  list_display = ('username', 'is_superuser')
  search_fields = ('username',)
  fieldsets = (
      (None, {
        'fields': (
          ('username', 'change_password'),
          ('member_link', 'organization_link')
        )
      }),
      ('Details', {
        'classes': ('collapse',),
        'fields': (
          ('date_joined', 'last_login'),
          ('is_staff', 'is_superuser'),
          'is_active'
        )
      })
  )
  readonly_fields = ('last_login', 'date_joined', 'change_password',
                     'member_link', 'organization_link')

  def member_link(self, obj):
    if hasattr(obj, 'member'):
      return utils.admin_change_link('fund_member', obj.member, new_tab=True)
    return '-'
  member_link.allow_tags = True
  member_link.short_description = 'Member'

  def organization_link(self, obj):
    if hasattr(obj, 'organization'):
      return utils.admin_change_link('grants_organization', obj.organization, new_tab=True)
    return '-'
  organization_link.allow_tags = True
  organization_link.short_description = 'Organization'

  def change_password(self, obj):
    return utils.create_link(reverse('admin:auth_user_password_change', args=(obj.pk,)),
                             'Change password')

  change_password.allow_tags = True
  change_password.short_description = 'Password'

admin.site.register(User, UserA)
