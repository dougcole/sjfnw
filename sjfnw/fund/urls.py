from django.conf.urls import url
from django.contrib.auth import views as auth_views

from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm
from sjfnw.fund import views as fund_views

urlpatterns = [

  # login, logout, registration
  url(r'^fund/login/?$', fund_views.fund_login),
  url(r'^fund/register/?$', fund_views.fund_register),
  url(r'^fund/logout/?$', auth_views.logout, {'next_page': '/fund'}),

  # main pages
  url(r'^fund/?$', fund_views.home),
  url(r'^fund/gp/?', fund_views.project_page),
  url(r'^fund/grants/?', fund_views.grant_list),

  # manage memberships
  url(r'^fund/projects/?', fund_views.manage_account),
  url(r'^fund/set-current/(?P<ship_id>\d+)/?', fund_views.set_current),

  # surveys
  url(r'^fund/survey/(?P<gp_survey_id>\d+)$', fund_views.project_survey),

  # forms - contacts
  url(r'^fund/add-contacts', fund_views.add_mult),
  url(r'^fund/(?P<donor_id>\d+)/edit', fund_views.edit_contact),
  url(r'^fund/(?P<donor_id>\d+)/delete', fund_views.delete_contact),
  url(r'^fund/add-estimates', fund_views.add_estimates),
  url(r'^fund/copy', fund_views.copy_contacts),

  # forms - steps
  url(r'^fund/(?P<donor_id>\d+)/step$', fund_views.add_step),
  url(r'^fund/stepmult$', fund_views.add_mult_step),
  url(r'^fund/(?P<donor_id>\d+)/(?P<step_id>\d+)$', fund_views.edit_step),
  url(r'^fund/(?P<donor_id>\d+)/(?P<step_id>\d+)/done', fund_views.complete_step),

  # error/help pages
  url(r'^fund/not-member/?', fund_views.not_member),
  url(r'^fund/pending/?$', fund_views.not_approved),
  url(r'^fund/support/?', fund_views.support),
  url(r'^fund/blocked/?$', fund_views.blocked),

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
    'fund-reset'
  ),
  url(r'^fund/reset-complete/?$', auth_views.password_reset_complete, {
    'template_name': 'fund/reset_password_complete.html'
  }),
]
