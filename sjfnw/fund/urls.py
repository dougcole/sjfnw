from django.conf.urls import url
from django.contrib.auth import views as auth_views

from sjfnw.constants import FUND_EMAIL
from sjfnw.fund import views

urlpatterns = [

  # login, logout, registration
  url(r'^login/?$', views.fund_login, name='login'),
  url(r'^register/?$', views.fund_register, name='register'),
  url(r'^logout/?$', auth_views.logout, {'next_page': '/fund/'}),

  # main pages
  url(r'^$', views.home, name='home'),
  url(r'^gp/?', views.project_page, name='project_page'),
  url(r'^grants/?', views.grant_list, name='gp_grants'),

  # manage memberships
  url(r'^projects/?', views.manage_account, name='account'),
  url(r'^set-current/(\d+)/?', views.set_current, name='set_current'),

  # surveys
  url(r'^survey/(\d+)$', views.project_survey, name='project_survey'),

  url(r'^add-contacts', views.add_mult, name='add_contacts'),
  url(r'^(\d+)/edit', views.edit_contact, name='edit_contact'),
  url(r'^(\d+)/delete', views.delete_contact, name='delete_contact'),
  url(r'^add-estimates', views.add_estimates, name='add_estimates'),
  url(r'^copy', views.copy_contacts, name='copy_contacts'),

  # forms - steps
  url(r'^(\d+)/step$', views.add_step, name='add_step'),
  url(r'^stepmult$', views.add_mult_step, name='add_mult_step'),
  url(r'^(\d+)/(\d+)$', views.edit_step, name='edit_step'),
  url(r'^(\d+)/(\d+)/done', views.complete_step, name='complete_step'),

  # error/help pages
  url(r'^not-member/?', views.not_member, name='not_member'),
  url(r'^pending/?$', views.not_approved, name='not_approved'),
  url(r'^support/?', views.support, name='support'),
  url(r'^blocked/?$', views.blocked, name='blocked'),

  # password reset
  url(r'^reset/?$', auth_views.password_reset,
    {
      'template_name': 'fund/reset_password_start.html',
      'from_email': FUND_EMAIL,
      'email_template_name': 'fund/emails/reset_password.html',
      'subject_template_name': 'registration/password_reset_subject.txt',
      'post_reset_redirect': '/fund/reset-sent'
    },
    name='reset_password_start'
  ),
  url(r'^reset-sent/?$', auth_views.password_reset_done,
    {'template_name': 'fund/reset_password_sent.html'},
    name='reset_sent'
  ),
  url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/?$',
    auth_views.password_reset_confirm,
    {
      'template_name': 'fund/reset_password.html',
      'post_reset_redirect': '/fund/reset-complete'
    },
    name='reset_password'
  ),
  url(r'^reset-complete/?$', auth_views.password_reset_complete,
    {'template_name': 'fund/reset_password_complete.html'},
    name='reset_complete'
  ),
]
