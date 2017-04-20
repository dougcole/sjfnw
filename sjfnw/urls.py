from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView, TemplateView

from sjfnw.grants.urls import apply_urls, report_urls, grants_urls, root_urls

handler404 = 'sjfnw.views.page_not_found'
handler500 = 'sjfnw.views.server_error'

if settings.MAINTENANCE:
  urlpatterns = [
    url(r'^maintenance$', 'sjfnw.views.maintenance'),
    url(r'', RedirectView.as_view(url='/maintenance')),
  ]
else:
  admin.autodiscover() # load admin.py from all apps

  urlpatterns = [
    url(r'^/?$', TemplateView.as_view(template_name='home.html'), name='index'),

    # project central
    url(r'^fund/', include('sjfnw.fund.urls', app_name='fund')),
    url(r'^fund$', RedirectView.as_view(url='/fund/')),

    # grants
    url(r'^apply/', include(apply_urls, app_name='grants')),
    url(r'^apply$', RedirectView.as_view(url='/apply/')),
    url(r'^org/?$', RedirectView.as_view(url='/apply/')),
    url(r'^grants/', include(grants_urls, app_name='grants')),
    url(r'^report/', include(report_urls, app_name='grants')),
    url(r'^', include(root_urls, app_name='grants')),

    # admin
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin$', RedirectView.as_view(url='/admin/')),
    url(r'^admin/grants/grantapplication/(?P<app_id>\d+)/revert',
      'sjfnw.grants.views.revert_app_to_draft'),
    url(r'^admin/grants/grantapplication/(?P<app_id>\d+)/rollover',
      'sjfnw.grants.views.admin_rollover'),
    url(r'^admin/grants/organization/login', 'sjfnw.grants.views.login_as_org'),
    url(r'^admin/grants/givingprojectgrant/yer-status', 'sjfnw.grants.views.show_yer_statuses'),

    url(r'^admin/grants/organizations/merge/(?P<id_a>\d+)/(?P<id_b>\d+)',
      'sjfnw.grants.views.merge_orgs'),

    # reporting
    url(r'^admin/grants/search/?', 'sjfnw.grants.views.grants_report'),

    # cron emails
    url(r'^mail/overdue-step', 'sjfnw.fund.cron.email_overdue'),
    url(r'^mail/new-accounts', 'sjfnw.fund.cron.new_accounts'),
    url(r'^mail/gifts', 'sjfnw.fund.cron.gift_notify'),
    url(r'^mail/drafts/?', 'sjfnw.grants.cron.draft_app_warning'),
    url(r'^mail/yer/?', 'sjfnw.grants.cron.yer_reminder_email'),

    # dev
    url(r'^dev/jslog/?', 'sjfnw.views.log_javascript')
  ]

  # for dev_appserver
  urlpatterns += staticfiles_urlpatterns()

  # uncomment to support django debug toolbar
  # import debug_toolbar
  # urlpatterns += [
  #   (r'^__debug__/', include(debug_toolbar.urls)),
  # ]
