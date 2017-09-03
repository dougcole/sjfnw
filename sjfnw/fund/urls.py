from django.conf.urls import url
from django.contrib.auth import views as auth_views

from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm
from sjfnw.fund import views

app_name = 'fund'

urlpatterns = [

  url(r'^fund/login/?$', views.fund_login, name='login'),
  url(r'^fund/register/?$', views.fund_register, name='register'),
  url(r'^fund/logout/?$', auth_views.logout, {'next_page': '/fund'}),

  # main pages
  url(r'^fund/?$', views.home, name='home'),
  url(r'^fund/gp/?', views.project_page, name='project_page'),
  url(r'^fund/grants/?', views.grant_list, name='grants'),

  # manage memberships
  url(r'^fund/projects/?', views.manage_account, name='manage_account'),
  url(r'^fund/set-current/(?P<ship_id>\d+)/?', views.set_current, name='set_current'),

  # surveys
  url(r'^fund/survey/(?P<gp_survey_id>\d+)$', views.project_survey, name='project_survey'),

  # forms - contacts
  url(r'^fund/add-contacts', views.add_mult, name='add_contacts'),
  url(r'^fund/(?P<donor_id>\d+)/edit', views.edit_contact, name='edit_contact'),
  url(r'^fund/(?P<donor_id>\d+)/delete', views.delete_contact, name='delete_contact'),
  url(r'^fund/add-estimates', views.add_estimates, name='add_estimates'),
  url(r'^fund/copy', views.copy_contacts, name='copy_contacts'),

  # forms - steps
  url(r'^fund/(?P<donor_id>\d+)/step$', views.add_step, name='add_step'),
  url(r'^fund/stepmult$', views.add_mult_step, name='add_steps'),
  url(r'^fund/(?P<donor_id>\d+)/(?P<step_id>\d+)$', views.edit_step, name='edit_step'),
  url(r'^fund/(?P<donor_id>\d+)/(?P<step_id>\d+)/done', views.complete_step, name='complete_step'),

  # error/help pages
  url(r'^fund/not-member/?', views.not_member, name='not_member'),
  url(r'^fund/pending/?$', views.not_approved, name='not_approved'),
  url(r'^fund/support/?', views.support, name='support'),
  url(r'^fund/blocked/?$', views.blocked, name='blocked'),

  # password reset
  url(r'^fund/reset/?$', auth_views.password_reset, {
    'template_name': 'fund/reset_password_start.html',
    'from_email': constants.FUND_EMAIL,
    'email_template_name': 'fund/emails/reset_password.html',
    'subject_template_name': 'registration/password_reset_subject.txt',
    'post_reset_redirect': '/fund/reset-sent',
    'password_reset_form': CustomPasswordResetForm
  }),
  url(r'^fund/reset-sent/?$', auth_views.password_reset_done, {
    'template_name': 'fund/reset_password_sent.html'
  }),
  url(r'^fund/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    auth_views.password_reset_confirm, {
      'template_name': 'fund/reset_password.html',
      'post_reset_redirect': '/fund/reset-complete'
      },
    name='reset_confirm'
  ),
  url(r'^fund/reset-complete/?$', auth_views.password_reset_complete, {
    'template_name': 'fund/reset_password_complete.html'
  }),
]
