import logging

from sjfnw import constants as c, utils

logger = logging.getLogger('sjfnw')

def notify_approval(membership):
  to_email = membership.member.user.username
  utils.send_email(
    subject='Membership Approved',
    sender=c.FUND_EMAIL,
    to=[to_email],
    template='fund/emails/account_approved.html',
    context={
      'login_url': c.APP_BASE_URL + '/fund/login',
      'project': membership.giving_project
    }
  )
  logger.info(u'Approval email sent to %s at %s', membership, to_email)
