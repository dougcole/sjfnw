from django.contrib.auth import views as auth_views
from django.conf.urls import url
from django.views.generic.base import RedirectView, TemplateView

from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm
from sjfnw.grants import views as grants_views

urlpatterns = [
  url(r'^org/?$', RedirectView.as_view(url='/apply/')),

  url(r'^apply/submitted/?', TemplateView.as_view(template_name='grants/submitted.html')),

  # login, logout, registration
  url(r'^apply/login/?$', grants_views.org_login),
  url(r'^apply/register/?$', grants_views.org_register),
  url(r'^apply/nr', grants_views.not_registered),
  url(r'^apply/logout/?$', auth_views.logout, {'next_page': '/apply'}),

  # home page
  url(r'^apply/$', grants_views.org_home),
  url(r'^apply/draft/(?P<draft_id>\d+)/?$', grants_views.discard_draft),
  url(r'^apply/copy/?$', grants_views.copy_app),
  url(r'^apply/support/?', grants_views.org_support),

  # application
  url(r'^apply/(?P<cycle_id>\d+)/?$', grants_views.grant_application),
  url(r'^apply/info/(?P<cycle_id>\d+)/?$', grants_views.cycle_info),

  # application ajax
  url(r'^apply/(?P<cycle_id>\d+)/autosave/?$', grants_views.autosave_app),

  url(r'^(?P<draft_type>.*)/(?P<draft_id>\d+)/add-file/?$', grants_views.add_file),
  url(r'^(?P<draft_type>.*)/(?P<draft_id>\d+)/remove/(?P<file_field>.*)/?$', grants_views.remove_file),

  url(r'^get-upload-url/?', grants_views.get_upload_url),

  # year-end report
  url(r'^report/(?P<award_id>\d+)/?$', grants_views.year_end_report),
  url(r'^report/(?P<award_id>\d+)/autosave/?$', grants_views.autosave_yer),
  url(r'^report/view/(?P<report_id>\d+)/?$', grants_views.view_yer),
  url(r'^report/rollover/?$', grants_views.rollover_yer),

  url(r'^report/submitted/?', TemplateView.as_view(template_name='grants/yer_submitted.html')),

  # password reset
  url(r'^apply/reset/?$', auth_views.password_reset, {
    'template_name': 'grants/reset.html',
    'from_email': constants.GRANT_EMAIL,
    'email_template_name': 'grants/password_reset_email.html',
    'post_reset_redirect': '/apply/reset-sent',
    'password_reset_form': CustomPasswordResetForm
  }),
  url(r'^apply/reset-sent/?$', auth_views.password_reset_done, {
    'template_name': 'grants/password_reset_done.html'
  }),
  url(r'^apply/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    auth_views.password_reset_confirm, {
      'template_name': 'grants/password_reset_confirm.html',
      'post_reset_redirect': '/apply/reset-complete'
    }, 'org-reset'),
  url(r'^apply/reset-complete/?', auth_views.password_reset_complete, {
      'template_name': 'grants/password_reset_complete.html'
  }),

  # reading
  url(r'^grants/view/(?P<app_id>\d+)/?$', grants_views.view_application),
  url(r'^grants/(?P<obj_type>.*)-file/(?P<obj_id>\d+)-(?P<field_name>.*)', grants_views.view_file),
]
