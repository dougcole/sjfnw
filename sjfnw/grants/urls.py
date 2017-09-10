from django.contrib.auth import views as auth_views
from django.conf.urls import url
from django.views.generic.base import RedirectView, TemplateView

from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm
from sjfnw.grants import views

app_name = 'grants'

urlpatterns = [
  url(r'^org/?$', RedirectView.as_view(url='/apply/')),

  url(r'^apply/submitted/?', TemplateView.as_view(template_name='grants/submitted.html')),

  # login, logout, registration
  url(r'^apply/login/?$', views.org_login, name='login'),
  url(r'^apply/register/?$', views.org_register, name='register'),
  url(r'^apply/nr', views.not_registered),
  url(r'^apply/logout/?$', auth_views.logout, {'next_page': '/apply'}),

  # home page
  url(r'^apply/?$', views.org_home, name='home'),
  url(r'^apply/draft/(?P<draft_id>\d+)/?$', views.discard_draft, name='discard_draft'),
  url(r'^apply/copy/?$', views.copy_app),
  url(r'^apply/support/?', views.org_support, name='support'),

  # application
  url(r'^apply/(?P<cycle_id>\d+)/?$', views.grant_application, name='grant_application'),
  url(r'^apply/info/(?P<cycle_id>\d+)/?$', views.cycle_info, name='cycle_info'),

  # application ajax
  url(r'^apply/(?P<cycle_id>\d+)/autosave/?$', views.autosave_app, name='autosave_app'),

  url(r'^(?P<draft_type>.*)/(?P<draft_id>\d+)/add-file/?$', views.add_file, name='add_file'),
  url(r'^(?P<draft_type>.*)/(?P<draft_id>\d+)/remove/(?P<file_field>.*)/?$',
    views.remove_file, name='remove_file'),

  url(r'^get-upload-url/?', views.get_upload_url),

  # year-end report
  url(r'^report/(?P<award_id>\d+)/?$', views.year_end_report, name='year_end_report'),
  url(r'^report/(?P<award_id>\d+)/autosave/?$', views.autosave_yer, name='autosave_yer'),
  url(r'^report/view/(?P<report_id>\d+)/?$', views.view_yer, name='view_yer'),
  url(r'^report/rollover/?$', views.rollover_yer, name='rollover_yer'),

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
    auth_views.password_reset_confirm,
    {
      'template_name': 'grants/password_reset_confirm.html',
      'post_reset_redirect': '/apply/reset-complete'
    },
    name='reset_confirm'),
  url(r'^apply/reset-complete/?', auth_views.password_reset_complete, {
    'template_name': 'grants/password_reset_complete.html'
  }),

  # reading
  url(r'^grants/view/(?P<app_id>\d+)/?$', views.view_application, name='view_application'),
  url(r'^grants/(?P<obj_type>.*)-file/(?P<obj_id>\d+)-(?P<field_name>.*)',
      views.view_file, name='view_file'),
]
