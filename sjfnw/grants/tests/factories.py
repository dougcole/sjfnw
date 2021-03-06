import datetime
import json
import os
import random

from django.forms.models import model_to_dict
import factory
from faker import Faker

from sjfnw.fund.tests import factories as fund_factories
from sjfnw.grants import constants as gc, models, utils
from sjfnw.tests.factories import User as UserFactory

fake = Faker()

"""
  Factories to create instances of models for automated and manual testing
  See http://factoryboy.readthedocs.io/
"""

# pylint: disable=old-style-class

FILES_WITH_KEYS = [
  'fakeblobkey/{}'.format(name) for name in os.listdir('sjfnw/grants/tests/media/')
]
FILES = [
  name for name in os.listdir('sjfnw/grants/tests/media/')
]

class OrgUser(UserFactory):
  last_name = '(Organization)'


class Organization(factory.django.DjangoModelFactory):
  """ Minimal """

  class Meta:
    model = 'grants.Organization'

  name = factory.Sequence(lambda n: '{}{}'.format(fake.company(), n))
  user = factory.SubFactory(OrgUser, first_name=factory.SelfAttribute('..name'))


class OrganizationWithProfile(factory.django.DjangoModelFactory):
  """ Includes User. Does not includes staff-entered or fiscal sponsor fields """

  class Meta:
    model = 'grants.Organization'

  name = factory.Sequence(lambda n: '{}{}'.format(fake.company(), n))
  user = factory.SubFactory(OrgUser, first_name=factory.SelfAttribute('..name'))

  address = factory.Faker('street_address')
  city = factory.Faker('city')
  state = factory.LazyAttribute(lambda o: random.choice(gc.STATE_CHOICES)[0])
  zip = factory.Faker('zipcode')
  telephone_number = factory.Faker('phone_number')
  fax_number = factory.Faker('phone_number')
  email_address = factory.Faker('email')
  website = factory.Faker('url')
  contact_person = factory.Faker('name')
  contact_person_title = factory.Faker('job')

  status = factory.LazyAttribute(lambda o: random.choice(gc.STATUS_CHOICES[:3])[0])
  ein = factory.Faker('ean8')
  founded = factory.LazyAttribute(lambda o: random.randrange(1999, 2016))
  mission = factory.Faker('text')


class GrantCycle(factory.django.DjangoModelFactory):
  """ Special options:
    narrative_questions: list of name/version dicts (default: STANDARD_NARRATIVES)
    report_questions: list of name/version dicts (default: STANDARD_REPORT_QUESTIONS)
    status: 'open', 'closed', 'upcoming' (default: 'open')
    two_year_grants: whether to include two_year_grant question (default: False)
  """

  class Meta:
    model = 'grants.GrantCycle'

  class Params:
    status = 'open'
    two_year_grants = False

  title = factory.LazyAttribute(
    lambda o: '{} {} {}'.format(random.choice(CYCLE_NAMES), 'Grant Cycle', o.close.year)
  )
  open = factory.LazyAttribute(
    lambda o: fake.date_time_between(map_status[o.status][0], map_status[o.status][1])
  )
  close = factory.LazyAttribute(lambda o: get_close(o))
  info_page = factory.LazyAttribute(
    lambda o: 'http://socialjusticefund.org/grant-app/economic-justice-grant-2017'
  )

  @factory.post_generation
  def narrative_questions(self, create, questions, **kwargs):
    if not create:
      return

    questions = questions or gc.STANDARD_NARRATIVES
    if 'add' in kwargs:
      questions += kwargs['add']

    for i, question in enumerate(questions):
      narrative_question = models.NarrativeQuestion.objects.get(**question)
      cycle_narrative = CycleNarrative(
          narrative_question=narrative_question, grant_cycle=self, order=i + 1)
      cycle_narrative.save()

  @factory.post_generation
  def report_questions(self, create, questions, **kwargs):
    if not create:
      return

    questions = questions or gc.STANDARD_REPORT_QUESTIONS
    if 'add' in kwargs:
      questions += kwargs['add']

    for i, question in enumerate(questions):
      report_question = models.ReportQuestion.objects.get(
        name=question['name'], version=question['version'])
      cycle_report_question = models.CycleReportQuestion(
          report_question=report_question, grant_cycle=self, order=i + 1)
      cycle_report_question.save()


class GrantApplication(factory.django.DjangoModelFactory):
  """ Does not include: project support, fiscal sponsor,
      racial justice refs, admin fields
  """

  class Meta:
    model = 'grants.GrantApplication'

  organization = factory.SubFactory(Organization)
  grant_cycle = factory.SubFactory(GrantCycle)

  address = factory.Faker('street_address')
  city = factory.Faker('city')
  state = factory.LazyAttribute(lambda o: random.choice(gc.STATE_CHOICES)[0])
  zip = factory.Faker('zipcode')
  telephone_number = factory.Faker('phone_number')
  fax_number = factory.Faker('phone_number')
  email_address = factory.Faker('email')
  website = factory.Faker('url')
  contact_person = factory.Faker('name')
  contact_person_title = factory.Faker('job')

  status = factory.LazyAttribute(lambda o: random.choice(gc.STATUS_CHOICES[:3])[0])
  ein = factory.Faker('ean8')
  founded = factory.LazyAttribute(lambda o: random.randrange(1999, 2016))
  mission = factory.Faker('text')
  previous_grants = factory.Faker('text')

  start_year = factory.LazyAttribute(lambda o: random.randrange(1980, 2016))
  budget_last = factory.LazyAttribute(lambda o: random.randrange(1000, 800000))
  budget_current = factory.LazyAttribute(lambda o: random.randrange(1000, 800000))

  grant_request = factory.Faker('text')
  contact_person = factory.Faker('name')
  contact_person_title = factory.Faker('prefix')
  grant_period = factory.Faker('text')
  amount_requested = factory.LazyAttribute(lambda o: random.choice([10000, 100000]))

  support_type = 'General support'

  budget = factory.Iterator(FILES)
  demographics = factory.Iterator(FILES)
  funding_sources = factory.Iterator(FILES)
  budget1 = factory.Iterator(FILES)
  budget2 = factory.Iterator(FILES)
  budget3 = factory.Iterator(FILES)
  project_budget_file = factory.Iterator(FILES)

  @factory.post_generation
  def add_answers(self, create, *args, **kwargs): #pylint: disable=unused-argument
    if not create:
      return

    cycle_narratives = models.CycleNarrative.objects.filter(grant_cycle=self.grant_cycle)
    for cn in cycle_narratives:
      text = json.dumps(generate_narrative_answer(cn.narrative_question.name))
      answer = models.NarrativeAnswer(cycle_narrative=cn, grant_application=self, text=text)
      answer.save()


CYCLE_NAMES = [
  'Economic Justice', 'LGBTQ', 'Environmental Justice', 'General',
  'Immigration Justice', 'Gender Justice', 'Rural Justice', 'Movement Building'
]

map_status = {
  'open': ['-12w', '-1d'],
  'closed': ['-24w', '-5w'],
  'upcoming': ['+1d', '+12w']
}

def get_close(obj):
  if obj.status == 'open':
    return fake.date_time_between('+1d', '+5w')
  else:
    start = obj.open
    end = start + datetime.timedelta(weeks=random.randint(2, 12))
    return fake.date_time_between_dates(start, end)


class CycleNarrative(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.CycleNarrative'


def generate_narrative_answer(question_name, for_draft=False):
  values_list = None
  if question_name == 'timeline':
    values_list = ['A', 'b', 'c', 'D', 'e', 'f', 'G', 'h', 'i']
  elif question_name.endswith('_references'):
    values_list = [{
      'name': fake.name(),
      'org': fake.company(),
      'phone': fake.phone_number(),
      'email': fake.email()
      }, {
      'name': fake.name(),
      'org': fake.company(),
      'phone': fake.phone_number(),
      'email': fake.email()
    }]
    if for_draft:
      values_list = utils.flatten_references(values_list)
  if values_list and for_draft:
    return utils.multiwidget_list_to_dict(values_list, question_name)
  return values_list or fake.paragraph()


class DraftGrantApplication(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.DraftGrantApplication'

  organization = factory.SubFactory(Organization)
  grant_cycle = factory.SubFactory(GrantCycle)

  demographics = factory.Iterator(FILES)
  funding_sources = factory.Iterator(FILES)
  budget1 = factory.Iterator(FILES)
  budget2 = factory.Iterator(FILES)
  budget3 = factory.Iterator(FILES)
  project_budget_file = factory.Iterator(FILES)

  @factory.lazy_attribute
  def contents(self):
    app = GrantApplication.build() # pylint: disable=no-member
    fields_to_exclude = app.file_fields() + [
      'organization', 'grant_cycle', 'giving_projects', 'narratives', 'budget',
      'submission_time', 'pre_screening_status',
      'scoring_bonus_poc', 'scoring_bonus_geo'
    ]
    contents = model_to_dict(app, exclude=fields_to_exclude)
    qs = self.grant_cycle.narrative_questions.all() # pylint: disable=no-member
    for question in qs:
      result = generate_narrative_answer(question.name, for_draft=True)
      if isinstance(result, (unicode, str)):
        contents[question.name] = result
      else:
        contents.update(result)

    return json.dumps(contents)

class ProjectApp(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.ProjectApp'

  giving_project = factory.SubFactory(fund_factories.GivingProject)
  application = factory.SubFactory(GrantApplication)

  screening_status = factory.LazyFunction(lambda: random.choice(gc.SCREENING)[0])

class GivingProjectGrant(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.GivingProjectGrant'

  projectapp = factory.SubFactory(ProjectApp)

  amount = factory.LazyFunction(lambda: random.randrange(5000, 20000))

  first_report_due = factory.LazyFunction(lambda: fake.date_time_this_year(after_now=True).date())


def generate_report_answer(question):
  if question.input_type == gc.QuestionTypes.TEXT:
    return fake.paragraph()
  elif question.input_type == gc.QuestionTypes.SHORT_TEXT:
    return fake.text()
  elif question.input_type == gc.QuestionTypes.NUMBER:
    return random.randrange(2, 100)
  elif question.input_type == gc.QuestionTypes.PHOTO:
    return 'fakeblobkey{}/{}'.format(random.randrange(2, 100), fake.file_name(category='image'))
  elif question.input_type == gc.QuestionTypes.FILE:
    return 'fakeblobkey{}/{}'.format(random.randrange(2, 100), fake.file_name(category='office'))
  else:
    raise Exception('Unknown report question type {}'.format(question.input_type))

class GranteeReport(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.GranteeReport'

  giving_project_grant = factory.SubFactory(GivingProjectGrant)

  @factory.post_generation
  def add_answers(self, create, *args, **kwargs): #pylint: disable=unused-argument
    if not create:
      return

    cycle_report_questions = models.CycleReportQuestion.objects.filter(
      grant_cycle=self.giving_project_grant.projectapp.application.grant_cycle
    )
    for cycle_q in cycle_report_questions:
      text = generate_report_answer(cycle_q.report_question)
      answer = models.ReportAnswer(cycle_report_question=cycle_q, grantee_report=self, text=text)
      answer.save()
