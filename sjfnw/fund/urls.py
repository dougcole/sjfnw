from django.conf.urls import patterns
from sjfnw import constants
from sjfnw.forms import CustomPasswordResetForm

urlpatterns = patterns('sjfnw.fund.views',

  # login, logout, registration
  (r'^login/?$', 'fund_login'),
  (r'^register/?$', 'fund_register'),

  # main pages
  (r'^$', 'home'),
  (r'^gp/?', 'project_page'),
  (r'^grants/?', 'grant_list'),

  # manage memberships
  (r'^projects/?', 'manage_account'),
  (r'^set-current/(?P<ship_id>\d+)/?', 'set_current'),

  # surveys
  (r'^survey/(?P<gp_survey_id>\d+)$', 'project_survey'),

  # forms - contacts
  (r'^add-contacts', 'add_mult'),
  (r'^(?P<donor_id>\d+)/edit', 'edit_contact'),
  (r'^(?P<donor_id>\d+)/delete', 'delete_contact'),
  (r'^add-estimates', 'add_estimates'),
  (r'^copy', 'copy_contacts'),

  # forms - steps
  (r'^(?P<donor_id>\d+)/step$', 'add_step'),
  (r'^stepmult$', 'add_mult_step'),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)$', 'edit_step'),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)/done', 'complete_step'),

  # error/help pages
  (r'^not-member/?', 'not_member'),
  (r'^pending/?$', 'not_approved'),
  (r'^support/?', 'support'),
  (r'^blocked/?$', 'blocked'),
)

urlpatterns += patterns('',
  # password reset
  (r'^reset/?$', 'django.contrib.auth.views.password_reset', {
    'template_name': 'fund/reset_password_start.html',
    'from_email': constants.FUND_EMAIL,
    'email_template_name': 'fund/emails/reset_password.html',
    'subject_template_name': 'registration/password_reset_subject.txt',
    'post_reset_redirect': '/fund/reset-sent',
    'password_reset_form': CustomPasswordResetForm
  }),
  (r'^reset-sent/?$', 'django.contrib.auth.views.password_reset_done', {
    'template_name': 'fund/reset_password_sent.html'
  }),
  (r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    'django.contrib.auth.views.password_reset_confirm', {
      'template_name': 'fund/reset_password.html',
      'post_reset_redirect': '/fund/reset-complete'
    },
    'fund-reset'
  ),
  (r'^reset-complete/?$', 'django.contrib.auth.views.password_reset_complete', {
    'template_name': 'fund/reset_password_complete.html'
  }),
)
