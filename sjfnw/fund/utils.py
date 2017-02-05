import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from sjfnw import constants as c

logger = logging.getLogger('sjfnw')

def notify_approval(membership):
  subject, from_email = 'Membership Approved', c.FUND_EMAIL
  to_email = membership.member.user.username
  html_content = render_to_string('fund/emails/account_approved.html', {
    'login_url': c.APP_BASE_URL + '/fund/login',
    'project': membership.giving_project
  })
  text_content = strip_tags(html_content)
  msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email],
                               ['sjfnwads@gmail.com']) # bcc for testing
  msg.attach_alternative(html_content, 'text/html')
  msg.send()
  logger.info(u'Approval email sent to %s at %s', membership, to_email)
