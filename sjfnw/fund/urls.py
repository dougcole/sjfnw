from django.contrib.auth import views as auth_views
from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm
from sjfnw.fund import views as fund_views

urlpatterns = [

  # login, logout, registration
  (r'^login/?$', 'fund_login'),
  (r'^register/?$', fund_views.fund_register),

  # main pages
  (r'^$', fund_views.home),
  (r'^gp/?', fund_views.project_page),
  (r'^grants/?', fund_views.grant_list),

  # manage memberships
  (r'^projects/?', fund_views.manage_account),
  (r'^set-current/(?P<ship_id>\d+)/?', fund_views.set_current),

  # surveys
  (r'^survey/(?P<gp_survey_id>\d+)$', fund_views.project_survey),

  # forms - contacts
  (r'^add-contacts', fund_views.add_mult),
  (r'^(?P<donor_id>\d+)/edit', fund_views.edit_contact),
  (r'^(?P<donor_id>\d+)/delete', fund_views.delete_contact),
  (r'^add-estimates', fund_views.add_estimates),
  (r'^copy', fund_views.copy_contacts),

  # forms - steps
  (r'^(?P<donor_id>\d+)/step$', fund_views.add_step),
  (r'^stepmult$', fund_views.add_mult_step),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)$', fund_views.edit_step),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)/done', fund_views.complete_step),

  # error/help pages
  (r'^not-member/?', fund_views.not_member),
  (r'^pending/?$', fund_views.not_approved),
  (r'^support/?', fund_views.support),
  (r'^blocked/?$', fund_views.blocked),

  # password reset
  (r'^reset/?$', auth_views.password_reset, {
    'template_name': 'fund/reset_password_start.html',
    'from_email': constants.FUND_EMAIL,
    'email_template_name': 'fund/emails/reset_password.html',
    'subject_template_name': 'registration/password_reset_subject.txt',
    'post_reset_redirect': '/fund/reset-sent',
    'password_reset_form': CustomPasswordResetForm
  }),
  (r'^reset-sent/?$', auth_views.password_reset_done, {
    'template_name': 'fund/reset_password_sent.html'
  }),
  (r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    auth_views.password_reset_confirm, {
      'template_name': 'fund/reset_password.html',
      'post_reset_redirect': '/fund/reset-complete'
    },
    'fund-reset'
  ),
  (r'^reset-complete/?$', auth_views.password_reset_complete, {
    'template_name': 'fund/reset_password_complete.html'
  }),
]
