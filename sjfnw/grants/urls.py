from django.conf.urls import url
from django.views.generic.base import TemplateView

from sjfnw.constants import GRANT_EMAIL
from sjfnw.grants import views

apply_urls = [
  url(r'^submitted/?', TemplateView.as_view(template_name='grants/submitted.html')),

  # login, logout, registration
  url(r'^login/?$', views.org_login, name='login'),
  url(r'^register/?$', views.org_register, name='register'),
  url(r'^nr', views.not_registered, name='not_registered'),

  # home page
  url(r'^$', views.org_home, name='home'),
  url(r'^draft/(?P<draft_id>\d+)/?$', views.discard_draft, name='discard_draft'),
  url(r'^copy/?$', views.copy_app, name='copy_app'),
  url(r'^support/?', views.org_support, name='support'),

  # application
  url(r'^(\d+)/?$', views.grant_application, name='grant_application'),
  url(r'^info/(\d+)/?$', views.cycle_info, name='cycle_info'),

  # application ajax
  url(r'^(\d+)/autosave/?$', views.autosave_app, name='autosave_app')

  # password reset
  url(r'^reset/?$', 'django.contrib.auth.views.password_reset', {
    'template_name': 'grants/reset.html',
    'from_email': GRANT_EMAIL,
    'email_template_name': 'grants/password_reset_email.html',
    'post_reset_redirect': '/apply/reset-sent'
  }),
  url(r'^reset-sent/?$', 'django.contrib.auth.views.password_reset_done', {
    'template_name': 'grants/password_reset_done.html'
  }),
  url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    'django.contrib.auth.views.password_reset_confirm', {
      'template_name': 'grants/password_reset_confirm.html',
      'post_reset_redirect': '/apply/reset-complete'
    }, 'org-reset'),
  url(r'^reset-complete/?', 'django.contrib.auth.views.password_reset_complete', {
      'template_name': 'grants/password_reset_complete.html'
  }),
]

root_urls = [
  url(r'^(.*)/(\d+)/add-file/?$', views.add_file, name='add_file'),
  url(r'^(.*)/(\d+)/remove/(.*)/?$', views.remove_file, name='remove_file'),
  url(r'^get-upload-url/?', views.get_upload_url, name='get_upload_url'),
]

report_urls = [
  # year-end report
  url(r'^(\d+)/?$', views.year_end_report, name='year_end_report'),
  url(r'^(\d+)/autosave/?$', views.autosave_yer, name='autosave_yer'),
  url(r'^view/(\d+)/?$', views.view_yer, name='view_yer'),
  url(r'^rollover/?$', views.rollover_yer, name='rollover_yer'),
  url(r'^submitted/?', TemplateView.as_view(template_name='grants/yer_submitted.html')),
]

grants_urls = [
  # reading
  url(r'^view/(?P<app_id>\d+)/?$', 'view_application'),
  url(r'^(?P<obj_type>.*)-file/(?P<obj_id>\d+)-(?P<field_name>.*)', 'view_file'),
]
