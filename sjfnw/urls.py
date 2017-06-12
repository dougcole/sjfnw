from django.conf import settings
from django.conf.urls import patterns, include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView, TemplateView

from sjfnw.grants.urls import apply_urls, report_urls, grants_urls, root_urls

handler404 = 'sjfnw.views.page_not_found'
handler500 = 'sjfnw.views.server_error'

if settings.MAINTENANCE:
  urlpatterns = patterns('',
    (r'^maintenance$', 'sjfnw.views.maintenance'),
    (r'', RedirectView.as_view(url='/maintenance')),
  )
else:
  admin.autodiscover() # load admin.py from all apps

  urlpatterns = patterns('',
    (r'^/?$', TemplateView.as_view(template_name='home.html')),

    # project central
    (r'^fund$', 'sjfnw.fund.views.home'),
    (r'^fund/', include('sjfnw.fund.urls')),
    (r'^fund/logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/fund'}),

    # grants
    (r'^apply$', 'sjfnw.grants.views.org_home'),
    (r'^apply/', include(apply_urls)),
    (r'^grants/', include(grants_urls)),
    (r'^report/', include(report_urls)),
    (r'^', include(root_urls)),
    (r'^org/?$', RedirectView.as_view(url='/apply/')),
    (r'^logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/apply'}),
    (r'^get-upload-url/?', 'sjfnw.grants.views.get_upload_url'),

    # admin
    (r'^admin/', include(admin.site.urls)),
    (r'^admin$', RedirectView.as_view(url='/admin/')),
    (r'^admin/grants/grantapplication/(?P<app_id>\d+)/revert',
      'sjfnw.grants.views.revert_app_to_draft'),
    (r'^admin/grants/grantapplication/(?P<app_id>\d+)/rollover',
      'sjfnw.grants.views.admin_rollover'),
    (r'^admin/grants/organization/login', 'sjfnw.grants.views.login_as_org'),
    (r'^admin/grants/givingprojectgrant/yer-status', 'sjfnw.grants.views.show_yer_statuses'),

    (r'^admin/grants/organizations/merge/(?P<id_a>\d+)/(?P<id_b>\d+)',
      'sjfnw.grants.views.merge_orgs'),

    # reporting
    (r'^admin/grants/search/?', 'sjfnw.grants.views.grants_report'),

    # cron emails TODO use /cron instead of /mail?
    (r'^mail/overdue-step', 'sjfnw.fund.cron.email_overdue'),
    (r'^mail/new-accounts', 'sjfnw.fund.cron.new_accounts'),
    (r'^mail/gifts', 'sjfnw.fund.cron.gift_notify'),
    (r'^mail/drafts/?', 'sjfnw.grants.cron.draft_app_warning'),
    (r'^mail/yer/?', 'sjfnw.grants.cron.yer_reminder_email'),
    (r'^mail/create-cycles', 'sjfnw.grants.cron.auto_create_cycles'),

    # dev
    (r'^dev/jslog/?', 'sjfnw.views.log_javascript')
  )

  # for dev_appserver
  urlpatterns += staticfiles_urlpatterns()

  # uncomment to support django debug toolbar
  # import debug_toolbar
  # urlpatterns += patterns('',
  #   (r'^__debug__/', include(debug_toolbar.urls)),
  # )
