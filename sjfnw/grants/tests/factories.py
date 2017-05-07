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

  Models with foreign keys will pick from existing objects unless a value
  is passed in - except for Organization, which creates its own User
"""

FILES = os.listdir('sjfnw/grants/tests/media/')

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
    questions: list of name/version dicts (default: STANDARD_NARRATIVES)
    status: 'open', 'closed', 'upcoming' (default: 'open')
    two_year_grants: whether to include two_year_grant question (default: False)
  """

  class Meta:
    model = 'grants.GrantCycle'

  class Params:
    status = 'open'
    two_year_grants = False

  open = factory.LazyAttribute(lambda o: fake.date_time_between(map_status[o.status][0], map_status[o.status][1]))
  close = factory.LazyAttribute(lambda o: get_close(o))
  info_page = 'http://socialjusticefund.org/grant-app/economic-justice-grant-2017'
  title = factory.LazyAttribute(lambda o: '{} {} {}'.format(random.choice(CYCLE_NAMES), 'Grant Cycle', o.close.year))

  @factory.post_generation
  def questions(self, create, questions, **kwargs):
    if not create:
      return

    questions = questions or gc.STANDARD_NARRATIVES
    if 'add' in kwargs:
      questions += kwargs['add']

    for i, q in enumerate(questions):
      nq = models.NarrativeQuestion.objects.get(**q)
      cn = CycleNarrative(narrative_question=nq, grant_cycle=self, order=i)
      cn.save()


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

  status = factory.LazyAttribute(lambda o: random.choice(gc.STATUS_CHOICES)[0])
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
  def add_answers(self, create, *args, **kwargs):
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
  'closed': ['-1y', '-5w'],
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
  ls = None
  if question_name == 'timeline':
    ls = ['A', 'b', 'c', 'D', 'e', 'f', 'G', 'h', 'i']
  elif question_name.endswith('_references'):
    ls =  [{
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
      ls = utils.flatten_references(ls)
  if ls and for_draft:
    return utils.multiwidget_list_to_dict(ls, question_name)
  return ls or fake.paragraph()

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
    app = GrantApplication.build()
    fields_to_exclude = app.file_fields() + [
      'organization', 'grant_cycle', 'giving_projects', 'narratives', 'budget',
      'submission_time', 'pre_screening_status',
      'scoring_bonus_poc', 'scoring_bonus_geo'
    ]
    contents = model_to_dict(app, exclude=fields_to_exclude)
    qs = self.grant_cycle.narrative_questions.all()
    for q in qs:
      result = generate_narrative_answer(q.name, for_draft=True)
      if isinstance(result, (unicode, str)):
        contents[q.name] = result
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

  first_yer_due = factory.LazyFunction(lambda: fake.date_time_this_year(after_now=True).date())


class YearEndReport(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.YearEndReport'

  award = factory.SubFactory(GivingProjectGrant)

  contact_person = factory.LazyFunction(lambda: '{}, {}'.format(fake.name(), fake.job()))
  email = factory.Faker('email')
  phone = factory.Faker('phone_number')
  website = factory.Faker('url')

  summarize_last_year = factory.Faker('paragraph')
  goal_progress = factory.Faker('paragraph')
  quantitative_measures = factory.Faker('paragraph')
  evaluation = factory.Faker('paragraph')
  achieved = factory.Faker('paragraph')
  collaboration = factory.Faker('paragraph')
  new_funding = factory.Faker('paragraph')
  major_changes = factory.Faker('paragraph')

  total_size = factory.LazyFunction(lambda: random.randrange(2, 300))
  donations_count = factory.LazyFunction(lambda: random.randrange(20, 3000))
  donations_count_prev = factory.LazyFunction(lambda: random.randrange(20, 3000))

  other_comments = factory.Faker('paragraph')

  photo1 = factory.Iterator(FILES)
  photo2 = factory.Iterator(FILES)
  photo_release = factory.Iterator(FILES)

class YERDraft(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.YERDraft'

  award = factory.SubFactory(GivingProjectGrant)
  contents = '{}'

  photo1 = factory.Iterator(FILES)
  photo2 = factory.Iterator(FILES)
  photo_release = factory.Iterator(FILES)
