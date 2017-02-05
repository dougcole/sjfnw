import datetime
import logging

from django.http import HttpResponse
from django.utils import timezone

from sjfnw import constants as c, utils
from sjfnw.fund import models

logger = logging.getLogger('sjfnw')

def email_overdue(request):
  today = datetime.date.today()
  ships = models.Membership.objects.filter(giving_project__fundraising_deadline__gte=today)
  limit = today - datetime.timedelta(days=7)
  subject = 'Fundraising Steps'
  from_email = c.FUND_EMAIL

  for ship in ships:
    member = ship.member
    if not ship.emailed or (ship.emailed <= limit):
      count, step = ship.overdue_steps(get_next=True)
      if count > 0 and step:
        to_email = ship.member.user.username
        logger.info('%s has overdue step(s), emailing.', to_email)
        utils.send_email(
          subject=subject,
          to=[to_email],
          sender=from_email,
          template='fund/emails/overdue_steps.html',
          context={
            'login_url': c.APP_BASE_URL + '/fund/login', 'ship': ship, 'num': count,
            'step': step, 'base_url': c.APP_BASE_URL
          }
        )
        ship.emailed = today
        ship.save(skip=True)
  return HttpResponse('')


def new_accounts(request):
  """ Send GP leaders an email saying how many unapproved memberships exist

    Will continue emailing about the same membership until it's approved/deleted.
  """

  subject = 'Accounts pending approval'
  from_email = c.FUND_EMAIL

  active_gps = models.GivingProject.objects.filter(fundraising_deadline__gte=timezone.now().date())

  for gp in active_gps:
    memberships = models.Membership.objects.filter(giving_project=gp)
    need_approval = memberships.filter(approved=False).count()
    if need_approval > 0:
      leaders = memberships.filter(leader=True)
      to_emails = [leader.member.user.username for leader in leaders]
      if to_emails:
        utils.send_email(
          subject=subject,
          to=to_emails,
          sender=from_email,
          template='fund/emails/accounts_need_approval.html',
          context={
            'admin_url': c.APP_BASE_URL + '/admin/fund/membership/',
            'count': need_approval,
            'giving_project': unicode(gp),
            'support_email': c.SUPPORT_EMAIL
          }
        )
        logger.info('%d unapproved memberships in %s. Email sent to %s',
            need_approval, unicode(gp), ', '.join(to_emails))

  return HttpResponse('')

def gift_notify(request):
  """ Set gift received notifications on membership object and send an email
      Marks donors as notified """

  donors = (models.Donor.objects
      .select_related('membership__member')
      .filter(gift_notified=False)
      .exclude(received_this=0, received_next=0, received_afternext=0))

  memberships = {}
  for donor in donors:
    if donor.membership not in memberships:
      memberships[donor.membership] = []
    memberships[donor.membership].append(donor)

  login_url = c.APP_BASE_URL + '/fund/'
  subject = 'Gift or pledge received'
  from_email = c.FUND_EMAIL

  for ship, donor_list in memberships.iteritems():
    gift_str = ''
    for donor in donor_list:
      gift_str += u'${}  gift or pledge received from {}! '.format(donor.received(), donor)
    ship.notifications = gift_str
    ship.save(skip=True)

    utils.send_email(
      subject=subject,
      to=[ship.member.user.username],
      sender=from_email,
      template='fund/emails/gift_received.html',
      context={'login_url': login_url, 'gift_str': ship.notifications}
    )
    logger.info('Set gift notification and sent email to %s', ship.member.user.username)

  donors.update(gift_notified=True)
  return HttpResponse('')
