from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView, TemplateView

from sjfnw import views
from sjfnw.grants import views as grants_views, cron as grants_cron
from sjfnw.fund import views as fund_views, cron as fund_cron

handler404 = 'sjfnw.views.page_not_found'
handler500 = 'sjfnw.views.server_error'

if settings.MAINTENANCE:
  urlpatterns = [
    (r'^maintenance$', views.maintenance),
    (r'', RedirectView.as_view(url='/maintenance')),
  ]
else:
  admin.autodiscover() # load admin.py from all apps

  urlpatterns = [
    (r'^/?$', TemplateView.as_view(template_name='home.html')),

    # project central
    (r'^fund$', fund_views.home),
    (r'^fund/', include('sjfnw.fund.urls')),
    (r'^fund/logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/fund'}),

    # grants
    (r'^', include('sjfnw.grants.urls)),
    (r'^org/?$', RedirectView.as_view(url='/apply/')),
    (r'^logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/apply'}),
    (r'^get-upload-url/?', 'sjfnw.grants.views.get_upload_url'),

    # admin
    (r'^admin/', include(admin.site.urls)),
    (r'^admin$', RedirectView.as_view(url='/admin/')),
    (r'^admin/grants/grantapplication/(?P<app_id>\d+)/revert', grants_views.revert_app_to_draft),
    (r'^admin/grants/grantapplication/(?P<app_id>\d+)/rollover', grants_views.admin_rollover),
    (r'^admin/grants/organization/login', grants_views.login_as_org),
    (r'^admin/grants/givingprojectgrant/yer-status', grants_views.show_yer_statuses),

    (r'^admin/grants/organizations/merge/(?P<id_a>\d+)/(?P<id_b>\d+)', grants_views.merge_orgs),

    # reporting
    (r'^admin/grants/search/?', grants_views.grants_report),

    # cron emails TODO use /cron instead of /mail?
    (r'^mail/overdue-step', fund_cron.email_overdue),
    (r'^mail/new-accounts', fund_cron.new_accounts),
    (r'^mail/gifts', fund_cron.gift_notify),
    (r'^mail/drafts/?', grants_cron.draft_app_warning),
    (r'^mail/yer/?', grants_cron.yer_reminder_email),
    (r'^mail/create-cycles', grants_cron.auto_create_cycles),

    # dev
    (r'^dev/jslog/?', 'sjfnw.views.log_javascript')
  ]

  # for dev_appserver
  urlpatterns += staticfiles_urlpatterns()

  # uncomment to support django debug toolbar
  # import debug_toolbar
  # urlpatterns += patterns('',
  #   (r'^__debug__/', include(debug_toolbar.urls)),
  # )
