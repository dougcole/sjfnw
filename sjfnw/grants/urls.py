from django.conf.urls import patterns
from django.views.generic.base import TemplateView

from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm

apply_urls = patterns('',
  (r'^submitted/?', TemplateView.as_view(template_name='grants/submitted.html')),
)

apply_urls += patterns('sjfnw.grants.views',

  # login, logout, registration
  (r'^login/?$', 'org_login'),
  (r'^register/?$', 'org_register'),
  (r'^nr', 'not_registered'),

  # home page
  (r'^$', 'org_home'),
  (r'^draft/(?P<draft_id>\d+)/?$', 'discard_draft'),
  (r'^copy/?$', 'copy_app'),
  (r'^support/?', 'org_support'),

  # application
  (r'^(?P<cycle_id>\d+)/?$', 'grant_application'),
  (r'^info/(?P<cycle_id>\d+)/?$', 'cycle_info'),

  # application ajax
  (r'^(?P<cycle_id>\d+)/autosave/?$', 'autosave_app')
)

root_urls = patterns('sjfnw.grants.views',
  (r'^(?P<draft_type>.*)/(?P<draft_id>\d+)/add-file/?$', 'add_file'),
  (r'^apply/(?P<draft_id>\d+)/remove/(?P<file_field>.*)/?$', 'remove_file'),
  (r'^report/(?P<draft_id>\d+)/remove/(?P<file_field>.*)/?$', 'remove_report_file')
)

report_urls = patterns('sjfnw.grants.views',
  # grantee report
  (r'^draft/(?P<draft_id>\d+)/?$', 'discard_report_draft'),
  (r'^(?P<gpg_id>\d+)/?$', 'grantee_report'),
  (r'^(?P<gpg_id>\d+)/autosave/?$', 'autosave_grantee_report'),
  (r'^view/(?P<report_id>\d+)/?$', 'view_grantee_report'),
  # TODO: re-implement report rollover
  # (r'^rollover/?$', 'rollover_yer'),
)

report_urls += patterns('',
  (r'^submitted/?', TemplateView.as_view(template_name='grants/report_submitted.html')),
)

apply_urls += patterns('',
  # password reset
  (r'^reset/?$', 'django.contrib.auth.views.password_reset', {
    'template_name': 'grants/reset.html',
    'from_email': constants.GRANT_EMAIL,
    'email_template_name': 'grants/password_reset_email.html',
    'post_reset_redirect': '/apply/reset-sent',
    'password_reset_form': CustomPasswordResetForm
  }),
  (r'^reset-sent/?$', 'django.contrib.auth.views.password_reset_done', {
    'template_name': 'grants/password_reset_done.html'
  }),
  (r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    'django.contrib.auth.views.password_reset_confirm', {
      'template_name': 'grants/password_reset_confirm.html',
      'post_reset_redirect': '/apply/reset-complete'
    }, 'org-reset'),
  (r'^reset-complete/?', 'django.contrib.auth.views.password_reset_complete', {
      'template_name': 'grants/password_reset_complete.html'
  }),
)

grants_urls = patterns('sjfnw.grants.views',
  # reading
  (r'^view/(?P<app_id>\d+)/?$', 'view_application'),
  (r'^view-report/(?P<report_id>\d+)/?$', 'view_grantee_report'),
  (r'^report-draft/(?P<draft_id>\d+)/file/(?P<key>.*)?$', 'view_report_draft_file'),
  (r'^(?P<obj_type>.*)-file/(?P<obj_id>\d+)-(?P<field_name>.*)', 'view_file'),
  (r'^view-report-file/(?P<answer_id>.*)', 'view_file_direct'),
)
