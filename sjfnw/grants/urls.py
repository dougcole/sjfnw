from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView

from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm
from sjfnw.grants import views as grants_views

apply_urls = [
  (r'^submitted/?', TemplateView.as_view(template_name='grants/submitted.html')),

  # login, logout, registration
  (r'^login/?$', grants_views.org_login),
  (r'^register/?$', grants_views.org_register),
  (r'^nr', grants_views.not_registered),

  # home page
  (r'^$', grants_views.org_home),
  (r'^draft/(?P<draft_id>\d+)/?$', grants_views.discard_draft),
  (r'^copy/?$', grants_views.copy_app),
  (r'^support/?', grants_views.org_support),

  # application
  (r'^(?P<cycle_id>\d+)/?$', grants_views.grant_application),
  (r'^info/(?P<cycle_id>\d+)/?$', grants_views.cycle_info),

  # application ajax
  (r'^(?P<cycle_id>\d+)/autosave/?$', grants_views.autosave_app),

  (r'^(?P<draft_type>.*)/(?P<draft_id>\d+)/add-file/?$', grants_views.add_file),
  (r'^(?P<draft_type>.*)/(?P<draft_id>\d+)/remove/(?P<file_field>.*)/?$', grants_views.remove_file),

  # year-end report
  (r'^(?P<award_id>\d+)/?$', grants_views.year_end_report),
  (r'^(?P<award_id>\d+)/autosave/?$', grants_views.autosave_yer),
  (r'^view/(?P<report_id>\d+)/?$', grants_views.view_yer),
  (r'^rollover/?$', grants_views.rollover_yer),

  (r'^submitted/?', TemplateView.as_view(template_name='grants/yer_submitted.html')),

  # password reset
  (r'^reset/?$', auth_views.password_reset, {
    'template_name': 'grants/reset.html',
    'from_email': constants.GRANT_EMAIL,
    'email_template_name': 'grants/password_reset_email.html',
    'post_reset_redirect': '/apply/reset-sent',
    'password_reset_form': CustomPasswordResetForm
  }),
  (r'^reset-sent/?$', auth_views.password_reset_done, {
    'template_name': 'grants/password_reset_done.html'
  }),
  (r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    auth_views.password_reset_confirm, {
      'template_name': 'grants/password_reset_confirm.html',
      'post_reset_redirect': '/apply/reset-complete'
    }, 'org-reset'),
  (r'^reset-complete/?', auth_views.password_reset_complete, {
      'template_name': 'grants/password_reset_complete.html'
  }),

  # reading
  (r'^view/(?P<app_id>\d+)/?$', grants_views.view_application),
  (r'^(?P<obj_type>.*)-file/(?P<obj_id>\d+)-(?P<field_name>.*)', grants_views.view_file),
]
