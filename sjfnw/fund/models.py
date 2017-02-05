import datetime, json, logging

from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from sjfnw.fund.utils import notify_approval

logger = logging.getLogger('sjfnw')

class GivingProject(models.Model):
  title = models.CharField(max_length=255)

  public = models.BooleanField(default=True,
     help_text=('Whether this project should show in the dropdown menu for '
     'members registering or adding a project to their account.'))

  pre_approved = models.TextField(blank=True,
      help_text=('List of member emails, separated by commas. Anyone who '
      'registers using an email on this list will have their account '
      'automatically approved.  IMPORTANT: Any syntax error can make this '
      'feature stop working; in that case memberships will default to '
      'requiring manual approval by an administrator.'))

  fundraising_training = models.DateTimeField(
      help_text=('Date & time of fundraising training. At this point the app '
      'will require members to enter an ask amount & estimated likelihood for '
      'each contact.'))

  fundraising_deadline = models.DateField(
      help_text='Members will stop receiving reminder emails at this date.')

  fund_goal = models.PositiveIntegerField(default=0,
      verbose_name='Fundraising goal',
      help_text=('Fundraising goal agreed upon by the group. If 0, it will not '
        'be displayed to members and they won\'t see a group progress chart '
        'for money raised.'))

  suggested_steps = models.TextField(
      default=('Talk to about project\nInvite to SJF event\nSet up time to '
               'meet for the ask\nAsk\nFollow up\nThank'),
      help_text='Displayed to users when they add a step. Put each step on a new line')

  site_visits = models.BooleanField(default=False,
      help_text=('If checked, members will only see grants with a screening '
                'status of at least "site visit awarded"'))

  calendar = models.CharField(max_length=255, blank=True,
      help_text='Calendar ID of a google calendar - format: ____@group.calendar.google.com')

  resources = models.ManyToManyField('Resource', through='ProjectResource', blank=True)

  surveys = models.ManyToManyField('Survey', through='GPSurvey', blank=True)

  class Meta:
    ordering = ['-fundraising_deadline']

  def __unicode__(self):
    return u'{} {}'.format(self.title, self.fundraising_deadline.year)

  def save(self, *args, **kwargs):
    # prune CR (from Windows) that would result in extra line breaks
    self.suggested_steps = self.suggested_steps.replace('\r', '')
    super(GivingProject, self).save(*args, **kwargs)

  def get_suggested_steps(self):
    """ Return suggested steps as a list """
    suggested = self.suggested_steps.splitlines()
    # filter out empty lines, strip whitespace
    return [step.strip() for step in suggested if step and step.strip()]

  def is_pre_approved(self, email):
    """ Check new membership for pre-approval status """
    if self.pre_approved:
      approved_emails = [eml.strip().lower() for eml in self.pre_approved.split(',')]
      logger.info(u'Checking pre-approval for %s in %s. Pre-approved list: %s',
                  email, self, self.pre_approved)
      if email in approved_emails:
        return True
    return False

  def require_estimates(self):
    return self.fundraising_training <= timezone.now()

  def estimated(self):
    donors = Donor.objects.filter(membership__giving_project=self)
    estimated = 0
    for donor in donors:
      estimated += donor.estimated()
    return estimated


class MemberManager(models.Manager):

  def create_with_user(self, email=None, password=None, first_name=None, last_name=None):
    if User.objects.filter(username=email):
      raise ValueError('That email is already registered.')

    else:
      user = User.objects.create_user(email, password=password,
                                      first_name=first_name, last_name=last_name)
      member = self.model(user=user, first_name=first_name, last_name=last_name)
      member.save()
      return member


class Member(models.Model):
  objects = MemberManager()

  user = models.OneToOneField(User)
  first_name = models.CharField(max_length=100)
  last_name = models.CharField(max_length=100)

  giving_project = models.ManyToManyField(GivingProject, through='Membership')
  current = models.IntegerField(default=0) # pk of current membership

  def __unicode__(self):
    return u'{} {}'.format(self.first_name, self.last_name)

  class Meta:
    ordering = ['first_name', 'last_name']


class Membership(models.Model):
  """ Represents a relationship between a member and a giving project """

  giving_project = models.ForeignKey(GivingProject)
  member = models.ForeignKey(Member)
  approved = models.BooleanField(default=False)
  leader = models.BooleanField(default=False)

  # have they already been prompted to re-use contacts from previous gps
  copied_contacts = models.BooleanField(default=False)
  # json encoded list of gp eval surveys completed
  completed_surveys = models.CharField(max_length=255, default='[]')

  emailed = models.DateField(blank=True, null=True,
      help_text=('Last time this member was sent an overdue steps reminder'))
  last_activity = models.DateField(blank=True, null=True,
      help_text=('Last activity by this user on this membership.'))

  notifications = models.TextField(default='', blank=True)

  class Meta:
    ordering = ['member']
    unique_together = ('giving_project', 'member')

  def __unicode__(self):
    return u'{}, {}'.format(self.member, self.giving_project)

  def save(self, skip=False, *args, **kwargs):
    """ Checks whether to send an approval email unless skip is True """
    if not skip:
      try:
        previous = Membership.objects.get(pk=self.pk)
        logger.debug('Previously: %s, now %s ', previous.approved, self.approved)
        if self.approved and not previous.approved:
          logger.debug('Detected approval on save for ' + unicode(self))
          notify_approval(self)
      except Membership.DoesNotExist: # this is the first save for this membership
        pass
    super(Membership, self).save(*args, **kwargs)

  def get_progress(self):
    """ Compiles progress metrics (estimated, promised, received by year) """
    progress = {
      'estimated': 0,
      'promised': 0,
      'received_this': 0,
      'received_next': 0,
      'received_afternext': 0
    }
    donors = self.donor_set.all()

    for donor in donors:
      progress['estimated'] += donor.estimated()
      if donor.promised:
        progress['promised'] += donor.total_promised()
      progress['received_this'] += donor.received_this
      progress['received_next'] += donor.received_next
      progress['received_afternext'] += donor.received_afternext

    progress['received_total'] = (progress['received_this'] +
                                 progress['received_next'] +
                                 progress['received_afternext'])
    return progress

  def overdue_steps(self, get_next=False):
    cutoff = timezone.now().date() - datetime.timedelta(days=1)
    steps = Step.objects.filter(
        donor__membership_id=self.pk, completed__isnull=True, date__lt=cutoff
      ).order_by('-date')
    count = steps.count()
    if not get_next:
      return count
    elif count == 0:
      return count, False
    else:
      return count, steps[0]

  def update_story(self, timestamp):
    logger.info('update_story running for membership %d from %s', self.pk, timestamp)

    day_min = timestamp.replace(hour=0, minute=0, second=0)
    day_max = timestamp.replace(hour=23, minute=59, second=59)

    steps = Step.objects.filter(
        donor__membership_id=self.pk, completed__range=(day_min, day_max)
      ).select_related('donor')

    if not steps:
      logger.warning('update_story called on %d but no steps were completed', self.pk)
      return

    # get or create NewsItem instance
    logger.debug('Checking for story with date between %s and %s', day_min, day_max)
    search = self.newsitem_set.filter(date__range=(day_min, day_max))
    story = search[0] if search else NewsItem(date=timestamp, membership=self)

    # tally news-worthy milestones from steps
    talked, asked, promised = 0, 0, 0
    talkedlist = [] # used to make sure each individual donor only counts once
    askedlist = []
    for step in steps:
      if step.asked:
        asked += 1
        askedlist.append(step.donor_id)
        if step.donor_id in talkedlist: # don't count talked + asked for same donor
          talked -= 1
          talkedlist.remove(step.donor)
      elif step.donor not in talkedlist and step.donor not in askedlist:
        talked += 1
        talkedlist.append(step.donor)
      if step.promised and step.promised > 0:
        promised += step.promised

    # create summary blurb
    summary = self.member.first_name
    if talked > 0:
      summary += u' talked to {} {}'.format(talked, 'people' if talked > 1 else 'person')
      if asked > 0:
        if promised > 0:
          summary += u', asked {}'.format(asked)
        else:
          summary += u' and asked {}'.format(asked)
    elif asked > 0:
      summary += u' asked {} {}'.format(asked, 'people' if asked > 1 else 'person')
    else:
      logger.error('News update with 0 talked, 0 asked. Story pk: %d', story.pk)
    if promised > 0:
      summary += u' and got ${} in promises'.format(intcomma(promised))
    summary += u'.'
    logger.info(summary)
    story.summary = summary
    story.updated = timezone.now()
    story.save()
    logger.info('Story saved')


class Donor(models.Model):
  LIKELY_TO_JOIN_CHOICES = choices = (
      ('', '---------'),
      (3, '3 - Definitely'),
      (2, '2 - Likely'),
      (1, '1 - Unlikely'),
      (0, '0 - No chance'))
  added = models.DateTimeField(default=timezone.now)
  membership = models.ForeignKey(Membership)

  firstname = models.CharField(max_length=100, verbose_name='*First name')
  lastname = models.CharField(max_length=100, blank=True, verbose_name='Last name')

  amount = models.PositiveIntegerField(
      verbose_name='*Amount to ask ($)', null=True, blank=True)
  likelihood = models.PositiveIntegerField(
      verbose_name='*Estimated likelihood (%)',
      validators=[MaxValueValidator(100)], null=True, blank=True)

  talked = models.BooleanField(default=False)
  asked = models.BooleanField(default=False)
  promised = models.PositiveIntegerField(blank=True, null=True)
  # only if promised
  promise_reason = models.TextField(blank=True, default='[]') # json'd list of strings
  likely_to_join = models.PositiveIntegerField(null=True, blank=True,
      choices=LIKELY_TO_JOIN_CHOICES)
  received_this = models.PositiveIntegerField(default=0,
      verbose_name='Received - current year')
  received_next = models.PositiveIntegerField(default=0,
      verbose_name='Received - next year')
  received_afternext = models.PositiveIntegerField(default=0,
      verbose_name='Received - year after next')
  gift_notified = models.BooleanField(default=False)
  match_expected = models.PositiveIntegerField(blank=True, default=0,
      verbose_name='Match expected ($)', validators=[MinValueValidator(0)])
  match_company = models.CharField(max_length=255, blank=True, verbose_name='Employer name')
  match_received = models.PositiveIntegerField(blank=True, default=0,
      verbose_name='Match received ($)')

  # contact info only required if promise is entered
  phone = models.CharField(max_length=15, blank=True)
  email = models.EmailField(max_length=100, blank=True)
  notes = models.TextField(blank=True)

  class Meta:
    ordering = ['firstname', 'lastname']

  def __unicode__(self):
    if self.lastname:
      return self.firstname + u' ' + self.lastname
    else:
      return self.firstname

  def estimated(self):
    if self.amount and self.likelihood:
      return int(self.amount * self.likelihood * .01)
    else:
      return 0

  def get_next_step(self):
    steps = self.step_set.filter(completed__isnull=True)
    return steps[0] if steps else None

  def organize_steps(self):
    """ Set completed_steps (list) and next_step (Step) attributes on self """
    self.completed_steps = []
    for step in self.step_set.all():
      if step.completed:
        self.completed_steps.append(step)
      else:
        self.next_step = step
        self.next_step.overdue = self.next_step.date < timezone.localtime(timezone.now()).date()
    self.completed_steps.sort(key=lambda s: s.date)

  def promise_reason_display(self):
    return ', '.join(json.loads(self.promise_reason))

  def received(self):
    total_received = self.received_this + self.received_next + self.received_afternext
    if self.match_received:
      total_received += self.match_received
    return total_received

  def total_promised(self):
    return self.match_expected + (self.promised or 0)


class Step(models.Model):
  created = models.DateTimeField(default=timezone.now)
  date = models.DateField(verbose_name='Date')
  description = models.CharField(max_length=255, verbose_name='Description')
  donor = models.ForeignKey(Donor)
  completed = models.DateTimeField(null=True, blank=True)
  asked = models.BooleanField(default=False)
  promised = models.PositiveIntegerField(blank=True, null=True)

  def __unicode__(self):
    return u'{:%m/%d/%y} - {}'.format(self.date, self.description)


class NewsItem(models.Model):
  date = models.DateTimeField(default=timezone.now)
  updated = models.DateTimeField(default=timezone.now)
  membership = models.ForeignKey(Membership)
  summary = models.TextField()

  def __unicode__(self):
    return unicode(self.summary)


class Resource(models.Model):
  created = models.DateTimeField(null=True, blank=True, default=timezone.now)
  title = models.CharField(max_length=255)
  summary = models.TextField(blank=True)
  link = models.URLField()

  class Meta:
    ordering = ['title']

  def __unicode__(self):
    return self.title


class ProjectResource(models.Model): # ties resource to project
  giving_project = models.ForeignKey(GivingProject)
  resource = models.ForeignKey(Resource)
  session = models.CharField(max_length=255)

  def __unicode__(self):
    return u'{} - {} - {}'.format(self.giving_project, self.session, self.resource)


class Survey(models.Model):
  created = models.DateTimeField(default=timezone.now)
  updated = models.DateTimeField(default=timezone.now)
  updated_by = models.CharField(max_length=100, blank=True)

  title = models.CharField(max_length=255,
      help_text='Descriptive summary to aid in sharing survey templates between '
       'projects. For admin site only. E.g. \'GP session evaluation\', '
       '\'Race workshop evaluation\', etc.')
  intro = models.TextField(
      help_text=('Introductory text to display before the questions when form '
                 'is shown to GP members.'),
      default=('Please fill out this quick survey to let us know how the last '
               'meeting went.  Responses are anonymous, and once you fill out '
               'the survey you\'ll be taken to your regular home page.'))
  questions = models.TextField( # json encoded list of questions
      help_text=('Leave all of a question\'s choices blank if you want a '
                 'write-in response instead of multiple choice'),
      default=('[{"question": "Did we meet our goals? (1=not at all, '
               '5=completely)", "choices": ["1", "2", "3", "4", "5"]}]'))

  def __unicode__(self):
    return self.title

  def save(self, *args, **kwargs):
    super(Survey, self).save(*args, **kwargs)
    logger.info('Survey saved. Questions are: ' + self.questions)


class GPSurvey(models.Model):
  survey = models.ForeignKey(Survey)
  giving_project = models.ForeignKey(GivingProject)
  date = models.DateTimeField()

  def __unicode__(self):
    return u'{} - {}'.format(self.giving_project.title, self.survey.title)


class SurveyResponse(models.Model):
  date = models.DateTimeField(default=timezone.now)
  gp_survey = models.ForeignKey(GPSurvey)
  responses = models.TextField() # json encoded question-answer pairs

  def __unicode__(self):
    return u'Response to {} {:%m/%d/%y} survey'.format(
        self.gp_survey.giving_project.title, self.date)
