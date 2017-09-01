from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView, TemplateView

from sjfnw import views
from sjfnw.fund import urls as fund_urls, cron as fund_cron
from sjfnw.grants import urls as grants_urls, cron as grants_cron, views as grants_views

handler404 = 'sjfnw.views.page_not_found'
handler500 = 'sjfnw.views.server_error'

if settings.MAINTENANCE:
  urlpatterns = [
    url(r'^maintenance$', views.maintenance),
    url(r'', RedirectView.as_view(url='/maintenance')),
  ]
else:
  admin.autodiscover() # load admin.py from all apps

  urlpatterns = [
    url(r'^/?$', TemplateView.as_view(template_name='home.html')),

    # project central
    url(r'^fund/', include(fund_urls)),

    # grants
    url(r'^', include(grants_urls)),

    # admin
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin$', RedirectView.as_view(url='/admin/')),
    url(r'^admin/grants/grantapplication/(?P<app_id>\d+)/revert', grants_views.revert_app_to_draft),
    url(r'^admin/grants/grantapplication/(?P<app_id>\d+)/rollover', grants_views.admin_rollover),
    url(r'^admin/grants/organization/login', grants_views.login_as_org),
    url(r'^admin/grants/givingprojectgrant/yer-status', grants_views.show_yer_statuses),

    url(r'^admin/grants/organizations/merge/(?P<id_a>\d+)/(?P<id_b>\d+)', grants_views.merge_orgs),

    # reporting
    url(r'^admin/grants/search/?', grants_views.grants_report),

    # cron emails TODO use /cron instead of /mail?
    url(r'^mail/overdue-step', fund_cron.email_overdue),
    url(r'^mail/new-accounts', fund_cron.new_accounts),
    url(r'^mail/gifts', fund_cron.gift_notify),
    url(r'^mail/drafts/?', grants_cron.draft_app_warning),
    url(r'^mail/yer/?', grants_cron.yer_reminder_email),
    url(r'^mail/create-cycles', grants_cron.auto_create_cycles),

    # dev
    url(r'^dev/jslog/?', views.log_javascript)
  ]

  # for dev_appserver
  urlpatterns += staticfiles_urlpatterns()

  # uncomment to support django debug toolbar
  # import debug_toolbar
  # urlpatterns += patterns('',
  #   (r'^__debug__/', include(debug_toolbar.urls)),
  # )
