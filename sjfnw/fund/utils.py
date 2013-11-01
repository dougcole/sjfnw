﻿from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.humanize.templatetags.humanize import intcomma
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from sjfnw import constants
import logging, models
logger = logging.getLogger('sjfnw')

def UpdateStory(membership_id, time):

  logger.info('UpdateStory running for membership ' + str(membership_id) +
               ' from ' + str(time))

  try: #get membership
    membership = models.Membership.objects.get(pk = membership_id)
  except models.Membership.DoesNotExist:
    logger.error('Update story - membership ' + str(membership_id) +
                  ' does not exist')
    return HttpResponse("failure")

  #today's range
  today_min = time.replace(hour=0, minute=0, second=0)
  today_max = time.replace(hour=23, minute=59, second=59)

  #check for steps
  logger.debug("Getting steps")
  steps = models.Step.objects.filter(completed__range=(today_min, today_max), donor__membership = membership).select_related('donor')
  if not steps:
    return HttpResponse("no steps!!")

  #get or create newsitem object
  logger.debug('Checking for story with date between ' + str(today_min) +
                ' and ' + str(today_max))
  search = models.NewsItem.objects.filter(date__range=(today_min, today_max),
                                          membership=membership)
  if search:
    story = search[0]
  else:
    story = models.NewsItem(date = time, membership=membership, summary = '')

  #tally today's steps
  talked, asked, promised = 0, 0, 0
  talkedlist = [] #for talk counts, don't want to double up
  askedlist = []
  for step in steps:
    logger.debug(unicode(step))
    if step.asked:
      asked += 1
      askedlist.append(step.donor)
      if step.donor in talkedlist: #if donor counted already, remove
        talked -= 1
        talkedlist.remove(step.donor)
    elif not step.donor in talkedlist and not step.donor in askedlist:
      talked += 1
      talkedlist.append(step.donor)
    if step.promised and step.promised > 0:
      promised += step.promised
  summary = membership.member.first_name
  if talked > 0:
    summary += u' talked to ' + unicode(talked) + (u' people' if talked>1 else u' person')
    if asked > 0:
      if promised > 0:
        summary += u', asked ' + unicode(asked)
      else:
        summary += u' and asked ' + unicode(asked)
  elif asked > 0:
    summary += u' asked ' + unicode(asked) + (u' people' if asked>1 else u' person')
  else:
    logger.error('News update with 0 talked, 0 asked. Story pk: ' + str(story.pk))
  if promised > 0:
    summary += u' and got $' + unicode(intcomma(promised)) + u' in promises'
  summary += u'.'
  logger.info(summary)
  story.summary = summary
  story.updated = timezone.now()
  story.save()
  logger.info('Story saved')
  return HttpResponse("success")

def NotifyApproval(membership):
  subject, from_email = 'Membership Approved', constants.FUND_EMAIL
  to = membership.member.email
  html_content = render_to_string('fund/email_account_approved.html',
                                  {'login_url':settings.APP_BASE_URL + 'fund/login',
                                   'project':membership.giving_project})
  text_content = strip_tags(html_content)
  msg = EmailMultiAlternatives(subject, text_content, from_email, [to],
                               ['sjfnwads@gmail.com']) #bcc for testing
  msg.attach_alternative(html_content, "text/html")
  msg.send()
  logger.info('Approval email sent to ' + unicode(membership) + ' at ' + to)

