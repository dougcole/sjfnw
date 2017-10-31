from datetime import timedelta
import json, logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import BaseValidator, MinValueValidator
from django.utils.safestring import mark_safe
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone

from sjfnw.utils import create_link
from sjfnw.fund.models import GivingProject
from sjfnw.grants import constants as gc, utils

logger = logging.getLogger('sjfnw')

# Custom fields
#---------------

class BasicFileField(models.FileField):
  """ Sets standard defaults """

  def __init__(self, **kwargs):
    defaults = {'upload_to': '/', 'max_length': 255}
    defaults.update(kwargs)
    super(BasicFileField, self).__init__(**defaults)

# Validators
#------------

class WordLimitValidator(BaseValidator):
  """ Custom validator that checks number of words in a string """
  message = (u'This field has a maximum word count of %(limit_value)d '
              '(current count: %(show_value)d)')
  code = 'max_words'

  def compare(self, count_a, count_b):
    return count_a > count_b

  def clean(self, val):
    return len(utils.strip_punctuation_and_non_ascii(val).split())

def validate_file_extension(value):
  """ Method to validate extension of uploaded files
      (Before I knew how to create a validator like the one above) """
  value = value.name if hasattr(value, 'name') else value
  if not utils.has_allowed_file_ext(value):
    raise ValidationError(u'That file type is not supported.')

def validate_photo_file_extension(value):
  """ Method to validate file extension of uploaded photos.
      (Should probably be custom validator) """
  value = value.name if hasattr(value, 'name') else value
  if not utils.has_allowed_photo_file_ext(value):
    raise ValidationError(u'That file type is not supported. Please upload an '
        'image with one of these extensions: %s' % ', '.join(gc.PHOTO_FILE_TYPES))

# Organizations
#---------------

class OrganizationManager(models.Manager):

  def create_with_user(self, email=None, password=None, name=None):
    error_msg = self.model.check_registration(name, email)
    if error_msg:
      raise ValueError(error_msg)

    name_match = self.filter(name=name, user__isnull=True).first()
    if name_match:
      # Given name matches an existing Organization without User.
      # Register, but flag inactive pending admin approval
      name_match.user = User.objects.create_user(
        email, email, password, first_name=name[:29], last_name='(Organization)'
      )
      name_match.user.is_active = False
      name_match.user.save()
      name_match.save()
      return name_match

    user = User.objects.create_user(
      email, email, password, first_name=name[:29], last_name='(Organization)'
    )
    org = self.model(user=user, name=name)
    org.save()
    return org


class Organization(models.Model):
  objects = OrganizationManager()

  name = models.CharField(max_length=255, unique=True, error_messages={
    'unique': ('An organization with this name is already in the system. '
    'To add a separate org with the same name, add/alter the name to '
    'differentiate the two.')})
  user = models.OneToOneField(User, null=True, blank=True)

  # staff entered fields
  staff_contact_person = models.CharField(max_length=250, blank=True,
      verbose_name='Staff-entered contact person')
  staff_contact_person_title = models.CharField(max_length=100, blank=True,
      verbose_name='Title')
  staff_contact_email = models.EmailField(verbose_name='Email address',
      max_length=255, blank=True)
  staff_contact_phone = models.CharField(verbose_name='Phone number',
      max_length=20, blank=True)

  # fields below are autopopulated from the most recent grant application
  # see GrantApplication.save

  # contact info
  address = models.CharField(max_length=100, blank=True)
  city = models.CharField(max_length=50, blank=True)
  state = models.CharField(max_length=2, choices=gc.STATE_CHOICES, blank=True)
  zip = models.CharField(max_length=50, blank=True)
  telephone_number = models.CharField(max_length=20, blank=True)
  fax_number = models.CharField(max_length=20, blank=True)
  email_address = models.EmailField(max_length=100, blank=True)
  website = models.CharField(max_length=50, blank=True)
  contact_person = models.CharField(max_length=250, blank=True,
      verbose_name='Contact person')
  contact_person_title = models.CharField(max_length=100, blank=True,
      verbose_name='Title')

  # org info
  status = models.CharField(max_length=50, choices=gc.STATUS_CHOICES, blank=True)
  ein = models.CharField(max_length=50, blank=True,
      verbose_name="Organization's or Fiscal Sponsor Organization's EIN")
  founded = models.PositiveIntegerField(null=True, blank=True,
                                        verbose_name='Year founded')
  mission = models.TextField(blank=True)

  # fiscal sponsor info (if applicable)
  fiscal_org = models.CharField(verbose_name='Organization name',
                                max_length=255, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person',
                                   max_length=255, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone',
                                      max_length=25, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address',
                                  max_length=100, blank=True)
  fiscal_address = models.CharField(verbose_name='Address',
                                    max_length=255, blank=True)
  fiscal_city = models.CharField(verbose_name='City',
                                 max_length=50, blank=True)
  fiscal_state = models.CharField(verbose_name='State', max_length=2,
                                  choices=gc.STATE_CHOICES, blank=True)
  fiscal_zip = models.CharField(verbose_name='ZIP', max_length=50, blank=True)
  fiscal_letter = BasicFileField(null=True, blank=True)

  class Meta:
    ordering = ['name']

  def __unicode__(self):
    return self.name

  @staticmethod
  def get_profile_fields():
    return [
      'address', 'city', 'state', 'zip', 'telephone_number', 'fax_number',
      'email_address', 'website', 'contact_person', 'contact_person_title',
      'status', 'ein', 'founded', 'mission', 'fiscal_org', 'fiscal_person',
      'fiscal_telephone', 'fiscal_email', 'fiscal_address', 'fiscal_city',
      'fiscal_state', 'fiscal_zip', 'fiscal_letter'
    ]

  @classmethod
  def check_registration(cls, name, email):
    if cls.objects.filter(user__username=email).exists():
      return gc.FORM_ERRORS['email_registered']
    if User.objects.filter(username=email).exists():
      return gc.FORM_ERRORS['email_registered_pc']
    if cls.objects.filter(name__iexact=name, user__isnull=False).exists():
      return gc.FORM_ERRORS['org_registered']

  def get_email(self):
    if hasattr(self, 'user') and self.user is not None:
      return self.user.username
    else:
      return None

  def get_staff_entered_contact_info(self):
    return ', '.join([val for val in [
      self.staff_contact_person, self.staff_contact_person_title,
      self.staff_contact_phone, self.staff_contact_email
    ] if val])

  def has_app_or_draft(self, cycle_id):
    filters = {'organization_id': self.pk, 'grant_cycle_id': cycle_id}
    if DraftGrantApplication.objects.filter(**filters).exists():
      return True
    else:
      return GrantApplication.objects.filter(**filters).exists()

  def update_profile(self, app):
    for field in self.get_profile_fields():
      if hasattr(app, field):
        setattr(self, field, getattr(app, field))
    self.save()
    logger.info('Org profile updated - %s', self.name)

# Organizations
#---------------

class GrantCycleManager(models.Manager):

  def copy(self, source, title, open_date, close):
    new_cycle = self.model(
      title=title,
      open=open_date,
      close=close,
      amount_note=source.amount_note,
      info_page=source.info_page,
      email_signature=source.email_signature,
      private=source.private)
    new_cycle.save()
    for cn in CycleNarrative.objects.filter(grant_cycle=source):
      cn_new_cycle = CycleNarrative(
        grant_cycle=new_cycle, narrative_question=cn.narrative_question, order=cn.order
      )
      cn_new_cycle.save()
    logger.info('Created %s cycle as copy of %s', title, source.title)
    return new_cycle

class GrantCycle(models.Model):

  objects = GrantCycleManager()

  title = models.CharField(max_length=100)
  open = models.DateTimeField()
  close = models.DateTimeField()

  info_page = models.URLField()
  email_signature = models.TextField(blank=True)
  conflicts = models.TextField(blank=True,
      help_text='Track any conflicts of interest (automatic & personally '
      'declared) that occurred  during this cycle.')
  private = models.BooleanField(default=False,
      verbose_name='Private (will not be displayed to orgs, but can be '
      'accessed by anyone who has the direct link)')

  amount_note = models.CharField(blank=True,
    max_length=255,
    help_text='Text to display in parenthesis after "Amount Requested" in the grant application form')
  narrative_questions = models.ManyToManyField('NarrativeQuestion', through='CycleNarrative')
  report_questions = models.ManyToManyField('ReportQuestion', through='CycleReportQuestion')

  class Meta:
    ordering = ['-close', 'title']

  def __unicode__(self):
    return self.title

  def is_open(self):
    return self.open < timezone.now() < self.close

  def get_status(self):
    today = timezone.now()
    if self.close < today:
      return 'closed'
    elif self.open > today:
      return 'upcoming'
    else:
      return 'open'

  def get_type(self):
    if 'Rapid Response' in self.title:
      return 'rapid'
    elif 'Seed' in self.title:
      return 'seed'
    return 'standard'

  def get_open_display(self):
    """ Summary of cycle's open period: open and close dates """
    if self.get_type() == 'standard':
      return 'Open {:%m/%d/%y} to {:%m/%d/%y}'.format(
          timezone.localtime(self.open), timezone.localtime(self.close))
    return self.get_close_display()

  def get_close_display(self):
    """ Display when cycle closes. Intended for use while cycle is open """
    if self.get_type() == 'standard':
      return 'Closes {:%b %d %I:%M %p}'.format(timezone.localtime(self.close))
    else:
      return 'Next review cutoff: {:%b %d}'.format(timezone.localtime(self.close))

# Grant applications
#--------------------

class DraftManager(models.Manager):

  def create_from_submitted_app(self, app):
    """ Creates a new draft using contents of given GrantApplication
      Args: app - GrantApplication instance
      Returns: DraftGrantApplication instance (not saved to db)
    """
    if not isinstance(app, GrantApplication):
      raise ValueError('create_from_submitted_app must be called with GrantApplication instance')

    draft = self.model(organization=app.organization, grant_cycle=app.grant_cycle)

    # TODO store this somewhere instead of computing every time
    fields_to_exclude = app.file_fields() + [
      'organization', 'grant_cycle', 'giving_projects', 'narratives', 'budget',
      'submission_time', 'pre_screening_status',
      'scoring_bonus_poc', 'scoring_bonus_geo'
    ]
    contents = model_to_dict(app, exclude=fields_to_exclude)
    answers = (NarrativeAnswer.objects.filter(grant_application=app)
                  .select_related('cycle_narrative__narrative_question'))
    for answer in answers:
      name = answer.cycle_narrative.narrative_question.name
      text = answer.text
      if name == 'timeline' or name.endswith('_references'):
        text = json.loads(answer.text)
        if name.endswith('_references'):
          text = utils.flatten_references(text)
        contents.update(utils.multiwidget_list_to_dict(text, name))
      else:
        contents[name] = text

    draft.contents = json.dumps(contents)

    for field in app.file_fields():
      if hasattr(app, field):
        setattr(draft, field, getattr(app, field))

    draft.modified = timezone.now()
    return draft

  def copy(self, draft, cycle_id):
    """ Copy given draft to a new grant cycle """
    if not isinstance(draft, DraftGrantApplication):
      raise ValueError('DraftGrantApplication instance is required')
    new_draft = self.model(
      organization_id=draft.organization_id,
      grant_cycle_id=cycle_id,
      contents=draft.contents
    )
    for field in GrantApplication.file_fields():
      if hasattr(draft, field):
        setattr(new_draft, field, getattr(draft, field))
    new_draft.save()
    return new_draft


class DraftGrantApplication(models.Model):
  """ Autosaved draft application """
  objects = DraftManager()

  organization = models.ForeignKey(Organization)
  grant_cycle = models.ForeignKey(GrantCycle)
  created = models.DateTimeField(blank=True, default=timezone.now)
  modified = models.DateTimeField(blank=True, default=timezone.now)
  modified_by = models.CharField(blank=True, max_length=100)

  contents = models.TextField(default='{}') # json'd dictionary of form contents

  demographics = BasicFileField()
  funding_sources = BasicFileField()
  budget1 = BasicFileField(verbose_name='Annual statement')
  budget2 = BasicFileField(verbose_name='Annual operating budget')
  budget3 = BasicFileField(verbose_name='Balance sheet')
  project_budget_file = BasicFileField(verbose_name='Project budget')
  fiscal_letter = BasicFileField()

  extended_deadline = models.DateTimeField(blank=True, null=True,
      help_text='Allows this draft to be edited/submitted past the grant cycle close.')

  class Meta:
    unique_together = ('organization', 'grant_cycle')

  @classmethod
  def file_fields(cls):
    return [f.name for f in cls._meta.fields if isinstance(f, BasicFileField)]

  def __unicode__(self):
    return u'DRAFT: ' + self.organization.name + ' - ' + self.grant_cycle.title

  def editable(self):
    deadline = self.grant_cycle.close
    now = timezone.now()
    return (self.grant_cycle.open < now and deadline > now or
           (self.extended_deadline and self.extended_deadline > now))

  def overdue(self):
    return self.grant_cycle.close <= timezone.now()

  def recently_edited(self):
    return timezone.now() < self.modified + timedelta(seconds=35)


class GrantApplication(models.Model):
  """ Submitted grant application """

  # automated fields
  submission_time = models.DateTimeField(blank=True, default=timezone.now,
                                         verbose_name='Submitted')
  organization = models.ForeignKey(Organization)
  grant_cycle = models.ForeignKey(GrantCycle)

  # contact info
  address = models.CharField(max_length=100)
  city = models.CharField(max_length=50)
  state = models.CharField(max_length=2, choices=gc.STATE_CHOICES)
  zip = models.CharField(max_length=50)
  telephone_number = models.CharField(max_length=20)
  fax_number = models.CharField(max_length=20, blank=True,
      verbose_name='Fax number (optional)',
      error_messages={
        'invalid': u'Enter a 10-digit fax number (including area code).'
      })
  email_address = models.EmailField(max_length=100)
  website = models.CharField(max_length=50, blank=True,
                             verbose_name='Website (optional)')

  # org info
  status = models.CharField(max_length=50, choices=gc.STATUS_CHOICES)
  ein = models.CharField(max_length=50, verbose_name="Organization or Fiscal Sponsor EIN")
  founded = models.PositiveIntegerField(verbose_name='Year founded')
  mission = models.TextField(verbose_name="Mission statement", validators=[WordLimitValidator(150)])
  previous_grants = models.CharField(max_length=255, blank=True,
      verbose_name='Previous SJF grants awarded (amounts and year)')

  # budget info
  start_year = models.CharField(max_length=250, verbose_name='Start date of fiscal year')
  budget_last = models.PositiveIntegerField(verbose_name='Org. budget last fiscal year')
  budget_current = models.PositiveIntegerField(verbose_name='Org. budget this fiscal year')

  # this grant info
  grant_request = models.TextField(verbose_name="Briefly summarize the grant request",
                                   validators=[WordLimitValidator(100)])
  contact_person = models.CharField(max_length=250, verbose_name='Name',
                                    help_text='Contact person for this grant application')
  contact_person_title = models.CharField(max_length=100, verbose_name='Title')
  grant_period = models.CharField(max_length=250, blank=True,
                                  verbose_name='Grant period (if different than fiscal year)')
  amount_requested = models.PositiveIntegerField()

  SUPPORT_CHOICES = [('General support', 'General'), ('Project support', 'Project')]
  support_type = models.CharField(max_length=50, choices=SUPPORT_CHOICES, blank=True)
  project_title = models.CharField(
      max_length=250, blank=True, verbose_name='Project title (if applicable)')
  project_budget = models.PositiveIntegerField(
      null=True, blank=True, verbose_name='Project budget (if applicable)')

  # fiscal sponsor
  fiscal_org = models.CharField(verbose_name='Fiscal org. name', max_length=255, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person', max_length=255, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone', max_length=25, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address', max_length=70, blank=True)
  fiscal_address = models.CharField(verbose_name='Address', max_length=255, blank=True)
  fiscal_city = models.CharField(verbose_name='City', max_length=50, blank=True)
  fiscal_state = models.CharField(verbose_name='State', max_length=2,
                                  choices=gc.STATE_CHOICES, blank=True)
  fiscal_zip = models.CharField(verbose_name='ZIP', max_length=50, blank=True)

  narratives = models.ManyToManyField('CycleNarrative', through='NarrativeAnswer', blank=True)

  # files
  budget = BasicFileField( # no longer shown, but field holds file from early apps
    blank=True,
    validators=[validate_file_extension]
  )
  demographics = BasicFileField(
    validators=[validate_file_extension],
    verbose_name='Diversity chart'
  )
  funding_sources = BasicFileField(
    blank=True,
    validators=[validate_file_extension]
  )
  # pylint: disable=line-too-long
  budget1 = BasicFileField(
    blank=True,
    help_text='Statement of actual income and expenses for the most recent completed fiscal year. Upload in your own format, but do not send your annual report, tax returns, or entire audited financial statement.',
    validators=[validate_file_extension],
    verbose_name='Annual statement'
  )
  budget2 = BasicFileField(
    blank=True,
    help_text='Projection of all known and estimated income and expenses for the current fiscal year. You may upload in your own format or use our budget form. NOTE: If your fiscal year will end within three months of this grant application deadline, please also attach your operating budget for the next fiscal year, so that we can get a more accurate sense of your organization\'s situation.',
    validators=[validate_file_extension],
    verbose_name='Annual operating budget'
  )
  budget3 = BasicFileField(
    blank=True,
    help_text='This is a snapshot of your financial status at the moment: a brief, current statement of your assets, liabilities, and cash on hand. Upload in your own format.',
    validators=[validate_file_extension],
    verbose_name='Balance sheet'
  )
  project_budget_file = BasicFileField(
    blank=True,
    help_text='This is required only if you are requesting project-specific funds. Otherwise, it is optional. You may upload in your own format or use our budget form.',
    validators=[validate_file_extension],
    verbose_name='Project budget (if applicable)'
  )
  fiscal_letter = BasicFileField(
    blank=True,
    help_text='Letter from the sponsor stating that it agrees to act as your fiscal sponsor and supports Social Justice Fund\'s mission.',
    validators=[validate_file_extension],
    verbose_name='Fiscal sponsor letter'
  )
  # pylint: enable=line-too-long

  # admin fields
  pre_screening_status = models.IntegerField(choices=gc.PRE_SCREENING, default=10)
  giving_projects = models.ManyToManyField(GivingProject, through='ProjectApp', blank=True)
  scoring_bonus_poc = models.BooleanField(default=False,
      verbose_name='Scoring bonus for POC-led')
  scoring_bonus_geo = models.BooleanField(default=False,
      verbose_name='Scoring bonus for geographic diversity')
  site_visit_report = models.URLField(
      blank=True, help_text=('Link to the google doc containing the site '
      'visit report. This will be visible to all project members, but not the '
      'organization.'))

  class Meta:
    ordering = ['organization', 'submission_time']
    unique_together = ('organization', 'grant_cycle')

  @classmethod
  def fields_starting_with(cls, start):
    return [f for f in cls._meta.get_all_field_names() if f.startswith(start)]

  @classmethod
  def file_fields(cls):
    return [f.name for f in cls._meta.fields if isinstance(f, models.FileField)]

  @classmethod
  def get_field_names(cls):
    return [f for f in cls._meta.get_all_field_names()]

  def __unicode__(self):
    return '%s - %s' % (unicode(self.organization), unicode(self.grant_cycle))

  def get_file_name(self, field_name):
    file_attr = getattr(self, field_name)
    if file_attr and hasattr(file_attr, 'name'):
      file_info = file_attr.name.split('/', 1)
      if len(file_info) > 1:
        return file_info[1]
      else:
        return file_attr.name
    return ''

  def save(self, *args, **kwargs):
    """ Update org profile if it is the most recent app for the org """

    super(GrantApplication, self).save(*args, **kwargs)

    # check if there are more recent apps
    apps = GrantApplication.objects.filter(organization_id=self.organization_id,
                                           submission_time__gt=self.submission_time)

    if apps.exists():
      logger.info('App updated, not the most recent for org, regular save')
    else:
      self.organization.update_profile(self)

  def get_narrative_answer(self, name):
    try:
      answer = NarrativeAnswer.objects.get(
          grant_application=self, cycle_narrative__narrative_question__name=name)
      return answer.text
    except NarrativeAnswer.DoesNotExist:
      return ''


class NarrativeQuestion(models.Model):
  created = models.DateTimeField(blank=True, default=timezone.now)

  name = models.CharField(max_length=75,
    help_text='Short description of question topic, e.g. "mission", "racial_justice"'
  )
  version = models.CharField(
      max_length=40,
      help_text='Short description of this variation of the question, e.g. "standard" for general SJF use, "rapid" for rapid response cycles.')
  text = models.TextField(
      help_text='Text to display, in raw html. Don\'t include question number - that will be added automatically')
  word_limit = models.PositiveSmallIntegerField(
      blank=True,
      null=True,
      help_text='Word limit for the question. Ignored for some question types, such as timeline and references. If left blank, no word limit will be enforced.'
  )

  archived = models.DateField(blank=True, null=True)

  class Meta:
    ordering = ('name', 'version')

  def __unicode__(self):
    return u'{} ({})'.format(self.display_name(), self.version)

  def display_name(self):
    return self.name.replace('_', ' ').title()

  def uses_word_limit(self):
    return not (self.name.endswith('_references') or self.name == 'timeline')


class CycleNarrative(models.Model):
  narrative_question = models.ForeignKey(NarrativeQuestion)
  grant_cycle = models.ForeignKey(GrantCycle)

  order = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)], default=1)

  class Meta:
    ordering = ('order',)
    unique_together = ('grant_cycle', 'narrative_question')

  def __unicode__(self):
    return u'{}. {}'.format(self.order, self.narrative_question)


class NarrativeAnswer(models.Model):
  cycle_narrative = models.ForeignKey(CycleNarrative)
  grant_application = models.ForeignKey(GrantApplication)
  text = models.TextField()

  def get_question_text(self):
    return self.cycle_narrative.narrative_question.text

  def get_display_value(self):
    name = self.cycle_narrative.narrative_question.name

    if name == 'timeline':
      timeline = json.loads(self.text) if self.text else []
      html = (u'<table class="timeline_display">'
              '<tr>'
              '<td></td>'
              '<td>date range</td>'
              '<td>activities</td>'
              '<td>goals/objectives</td>'
              '</tr>')
      row = u'<tr><td class="left">q{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'
      for i in range(0, 15, 3):
        q = i / 3 + 1
        colA = timeline[i] if len(timeline) > i else ''
        colB = timeline[i + 1] if len(timeline) > i + 1 else ''
        colC = timeline[i + 2] if len(timeline) > i + 2 else ''
        html += row.format(q, colA, colB, colC)
      html += '</table>'
      return html
    elif name.endswith('_references'):
      value = json.loads(self.text) if self.text else []
      html = u'<table><tr><td>Name</td><td>Organization</td><td>Phone</td> <td>Email</td></tr>'
      empty = u'-'
      for i in [0, 1]:
        ref = value[i] if len(value) > i else {}
        html += u'<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
          ref.get('name', empty),
          ref.get('org', empty),
          ref.get('phone', empty),
          ref.get('email', empty)
        )
      return html + u'</table>'

    return self.text

  class Meta:
    unique_together = ('grant_application', 'cycle_narrative')


class ProjectApp(models.Model):
  """ Connection between a grant app and a giving project.

  Stores that project's screening and site visit info related to the app """

  giving_project = models.ForeignKey(GivingProject)
  application = models.ForeignKey(GrantApplication)

  screening_status = models.IntegerField(choices=gc.SCREENING, blank=True, null=True)

  class Meta:
    unique_together = ('giving_project', 'application')

  def __unicode__(self):
    return '%s - %s' % (self.giving_project.title, self.application)


class GrantApplicationLog(models.Model):
  date = models.DateTimeField(default=timezone.now)
  organization = models.ForeignKey(Organization)
  application = models.ForeignKey(GrantApplication, null=True, blank=True,
      help_text=('Optional - if this log entry relates to a specific grant '
                 'application, select it from the list'))
  staff = models.ForeignKey(User)
  contacted = models.CharField(max_length=255, blank=True,
      help_text='Person from the organization that you talked to, if applicable.')
  notes = models.TextField()

  class Meta:
    ordering = ['-date']

  def __unicode__(self):
    return 'Log entry from {:%m/%d/%y}'.format(self.date)


# Grants (awards)
#-----------------

class GivingProjectGrant(models.Model):
  created = models.DateTimeField(default=timezone.now)

  projectapp = models.OneToOneField(ProjectApp)

  amount = models.DecimalField(max_digits=8, decimal_places=2)
  check_number = models.PositiveIntegerField(null=True, blank=True)
  check_mailed = models.DateField(null=True, blank=True)

  second_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
  second_check_number = models.PositiveIntegerField(null=True, blank=True)
  second_check_mailed = models.DateField(null=True, blank=True)

  agreement_mailed = models.DateField(null=True, blank=True)
  agreement_returned = models.DateField(null=True, blank=True)
  approved = models.DateField(verbose_name='Date approved by the ED', null=True, blank=True)

  first_report_due = models.DateField(verbose_name='First grantee report due date')
  second_report_due = models.DateField(null=True, blank=True,
    verbose_name='Second grantee report due date (if applicable)')

  class Meta:
    ordering = ['-created']

  def __unicode__(self):
    """ Basic description of grant: amount and duration """
    summary = u'${:,} '
    if self.grant_length() == 2:
      summary += 'two-year '
    summary += 'grant'
    return summary.format(self.total_amount())

  def full_description(self):
    """ Description of grant including the giving project that made the award.
        Not used as __unicode__ since it may trigger additional DB lookups """
    return u'{} from {}'.format(self, self.projectapp.giving_project)

  def agreement_due(self):
    """ Agreement is due 30 days after it is mailed
      Returns datetime.date or None if agreement has not been mailed
    """
    if self.agreement_mailed:
      return self.agreement_mailed + timedelta(days=30)
    else:
      return None

  # TODO delete
  def yers_due(self):
    completed = self.yearendreport_set.count()
    yers_due = []
    if completed == 0:
      yers_due.append(self.first_report_due)
    if self.second_report_due and completed < 2:
      yers_due.append(self.second_report_due)
    return yers_due

  def next_yer_due(self):
    """ Get
      Returns datetime.date or None if all YER have been submitted for this grant
    """
    completed = self.yearendreport_set.count()
    if completed == 0:
      return self.first_report_due
    elif completed == 1 and self.second_report_due:
      return self.second_report_due
    else:
      return None

  def total_amount(self):
    """ Total amount granted, or 0 if no amount has been entered """
    first_amount = self.amount or 0
    if self.second_amount:
      return self.second_amount + first_amount
    else:
      return first_amount

  def grant_length(self):
    """ Returns length of grant in years. Only supports 1 or 2 year grants """
    return 2 if self.second_amount else 1

  def fully_paid(self):
    if not self.check_mailed:
      return False
    if self.second_amount and not self.second_check_mailed:
      return False
    return True


class SponsoredProgramGrant(models.Model):
  entered = models.DateTimeField(default=timezone.now)
  organization = models.ForeignKey(Organization)
  amount = models.PositiveIntegerField()
  check_number = models.PositiveIntegerField(null=True, blank=True)
  check_mailed = models.DateField(null=True, blank=True)
  approved = models.DateField(verbose_name='Date approved by the ED',
                              null=True, blank=True)
  description = models.TextField(blank=True)

  class Meta:
    ordering = ['organization']

  def __unicode__(self):
    desc = 'Sponsored program grant - {}'.format(self.organization)
    if self.approved:
      desc += ' - {:%m/%d/%Y}'.format(self.approved)
    return desc


# Grantee reports
#-----------------

class GranteeReport(models.Model):
  giving_project_grant = models.ForeignKey(GivingProjectGrant)
  created = models.DateTimeField(default=timezone.now)

  report_number = models.IntegerField(default=1)
  cycle_report_questions = models.ManyToManyField('CycleReportQuestion',
      through='ReportAnswer')

  def __unicode__(self):
    return 'Grantee report: {}'.format(self.giving_project_grant)

  def get_organization(self):
    return self.giving_project_grant.projectapp.application.organization

  def get_grant_cycle(self):
    return self.giving_project_grant.projectapp.application.grant_cycle


class GranteeReportDraft(models.Model):
  giving_project_grant = models.ForeignKey(GivingProjectGrant)
  created = models.DateTimeField(default=timezone.now)
  modified = models.DateTimeField(default=timezone.now)
  contents = models.TextField(default='{}')
  files = models.TextField(default='{}')
  report_number = models.IntegerField(default=1)

  def get_due_date(self):
    award = self.giving_project_grant
    return award.first_report_due if self.report_number == 1 else award.second_report_due


class ReportQuestion(models.Model):
  created = models.DateTimeField(blank=True, default=timezone.now)

  name = models.CharField(max_length=75,
    help_text='Short description of question topic, e.g. "mission", "racial_justice"'
  )
  version = models.CharField(
    max_length=40,
    help_text='Short description of this variation of the question, e.g. "standard" for general SJF use, "rapid" for rapid response cycles.')
  text = models.TextField(
    help_text='Question text to display, in raw html. Don\'t include question number - that will be added automatically')
  input_type = models.CharField(
    choices=gc.QuestionTypes.choices(),
    max_length=20,
    default=gc.QuestionTypes.TEXT,
    help_text='Select the type of for input to use for this question.')
  word_limit = models.PositiveSmallIntegerField(
    default=750,
    help_text='Word limit for the question'
  )

  archived = models.DateField(blank=True, null=True)

  class Meta:
    ordering = ('name', 'version')

  def __unicode__(self):
    return u'{} ({})'.format(self.display_name(), self.version)

  def display_name(self):
    return self.name.replace('_', ' ').title()


class CycleReportQuestion(models.Model):
  report_question = models.ForeignKey(ReportQuestion)
  grant_cycle = models.ForeignKey(GrantCycle)

  order = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)], default=1)
  required = models.BooleanField(default=True)

  class Meta:
    ordering = ('order',)
    unique_together = ('grant_cycle', 'order')

  def __unicode__(self):
    return u'{}. {}'.format(self.order, self.report_question)


class ReportAnswer(models.Model):
  cycle_report_question = models.ForeignKey(CycleReportQuestion)
  grantee_report = models.ForeignKey(GranteeReport)
  text = models.TextField()

  class Meta:
    unique_together = ('grantee_report', 'cycle_report_question')

  def get_display(self):
    question_type = self.cycle_report_question.report_question.input_type
    if question_type == gc.QuestionTypes.FILE or question_type == gc.QuestionTypes.PHOTO:
      filename = self.text.split('/')[-1]
      url = reverse('sjfnw.grants.views.view_file_direct', kwargs={'answer_id': self.pk})
      return mark_safe(create_link(url, filename, new_tab=True))
    elif self.cycle_report_question.report_question.name == 'stay_informed':
      try:
        return '\n'.join([value for value in json.loads(self.text).values()])
      except:
        return 'Could not parse answer'
    else:
      return self.text

  def get_question_text(self):
    return self.cycle_report_question.report_question.text


class YearEndReport(models.Model):
  award = models.ForeignKey(GivingProjectGrant)
  submitted = models.DateTimeField(default=timezone.now)

  # user-entered
  contact_person = models.TextField() # Name, title (has custom widget)
  email = models.EmailField(max_length=255)
  phone = models.CharField(max_length=20)
  website = models.CharField(max_length=255) # autofill based on app

  summarize_last_year = models.TextField(verbose_name=(
      '1. Thinking about the Giving Project volunteers who decided to fund '
      'you last year, including those you met on your site visit, what would '
      'you like to tell them about what you\'ve done over the last year?'))
  goal_progress = models.TextField(verbose_name=(
      '2. Please refer back to your application from last year. Looking at '
      'the goals you outlined in your application, what progress have you '
      'made on each? If you were unable to achieve those goals or changed '
      'your direction, please explain why.'))
  quantitative_measures = models.TextField(verbose_name=(
      '3. Do you evaluate your work by any quantitative measures (e.g., number '
      'of voters registered, members trained, leaders developed, etc.)? If '
      'so, provide that information:'), blank=True)
  evaluation = models.TextField(verbose_name=(
      '4. What other type of evaluations do you use internally? Please share '
      'any outcomes that are relevant to the work funded by this grant.'))
  achieved = models.TextField(verbose_name=(
      '5. What specific victories, benchmarks, and/or policy changes (local, '
      'state, regional, or national) have you achieved over the past year?'))
  collaboration = models.TextField(verbose_name=(
      '6. What other organizations did you work with to achieve those '
      'accomplishments?'))
  new_funding = models.TextField(verbose_name=(
      '7. Did your grant from Social Justice Fund help you access any new '
      'sources of funding? If so, please explain.'), blank=True)
  major_changes = models.TextField(verbose_name=(
      '8. Describe any major staff or board changes or other major '
      'organizational changes in the past year.'), blank=True)
  total_size = models.PositiveIntegerField(verbose_name=(
      '9. What is the total size of your base? That is, how many people, '
      'including paid staff, identify as part of your organization?'))
  donations_count = models.PositiveIntegerField(verbose_name=(
      '10. How many individuals gave a financial contribution of any size to '
      'your organization in the last year?'))
  donations_count_prev = models.PositiveIntegerField(null=True, verbose_name=(
      'How many individuals made a financial contribution the previous year?'))

  stay_informed = models.TextField(verbose_name=(
    '11. What is the best way for us to stay informed about your work? '
    '(Enter any/all that apply)'), default='{}')

  other_comments = models.TextField(verbose_name=(
    '12. Other comments or information? Do you have any suggestions for how '
    'SJF can improve its grantmaking programs?'), blank=True) # json dict - see modelforms

  photo1 = models.FileField(validators=[validate_photo_file_extension],
      upload_to='/', max_length=255,
      help_text=('Please provide two or more photos that show your '
                 'organization\'s members, activities, etc. These pictures '
                 'help us tell the story of our grantees and of Social Justice '
                 'Fund to the broader public.'))
  photo2 = models.FileField(validators=[validate_photo_file_extension],
      upload_to='/', max_length=255)
  photo3 = models.FileField(validators=[validate_photo_file_extension],
      upload_to='/', help_text='(optional)', blank=True, max_length=255)
  photo4 = models.FileField(validators=[validate_photo_file_extension],
      upload_to='/', help_text='(optional)', blank=True, max_length=255)

  photo_release = models.FileField(upload_to='/', max_length=255,
    verbose_name=('Please provide photo releases signed by any people who '
                  'appear in these photos.'))

  # admin-entered
  visible = models.BooleanField(default=False, help_text=('Check this to make '
      'the YER visible to members of the GP that made the grant. (When '
      'unchecked, YER is only visible to staff and the org that submitted it.)'))

  def __unicode__(self):
    return 'Year-end report for ' + unicode(self.award)

  def stay_informed_display(self):
    display = []
    inf = json.loads(self.stay_informed)
    for key in inf:
      value = inf[key]
      if value:
        display.append(key + ': ' + value)
    return ', '.join(display)


class YERDraft(models.Model):

  award = models.ForeignKey(GivingProjectGrant)
  modified = models.DateTimeField(default=timezone.now)
  contents = models.TextField(default='{}')

  photo1 = BasicFileField(blank=True)
  photo2 = BasicFileField(blank=True)
  photo3 = BasicFileField(blank=True)
  photo4 = BasicFileField(blank=True)

  photo_release = BasicFileField()

  class Meta:
    verbose_name = 'Draft year-end report'

  def __unicode__(self):
    return 'DRAFT year-end report for ' + unicode(self.award)

  def is_overdue(self):
    return self.award.next_yer_due() < timezone.now().date()
