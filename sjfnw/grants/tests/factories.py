import random

import factory

from sjfnw.grants import constants as gc, models

class OrganizationFactory(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.Organization'

  name = factory.Faker('company')
  email = factory.Faker('email')

  # staff entered fields
  # staff_contact_person
  # staff_contact_person_title
  # staff_contact_email
  # staff_contact_phone

  # contact info
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

  # # org info
  status = factory.LazyAttribute(lambda o: random.choice(gc.STATUS_CHOICES)[0])
  ein = factory.Faker('ean8')
  founded = factory.LazyAttribute(lambda o: random.randrange(1999, 2016))
  mission = factory.Faker('text')

  # # fiscal sponsor info (if applicable)
  # fiscal_org
  # fiscal_person
  # fiscal_telephone
  # fiscal_email
  # fiscal_address
  # fiscal_city
  # fiscal_state
  # fiscal_zip
  # fiscal_letter

class GrantApplicationFactory(factory.django.DjangoModelFactory):

  class Meta:
    model = 'grants.GrantApplication'

  organization = factory.SubFactory(OrganizationFactory)
  grant_cycle = factory.Iterator(models.GrantCycle.objects.all())

  # contact info
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

  # # org info
  status = factory.LazyAttribute(lambda o: random.choice(gc.STATUS_CHOICES)[0])
  ein = factory.Faker('ean8')
  founded = factory.LazyAttribute(lambda o: random.randrange(1999, 2016))
  mission = factory.Faker('text')
  previous_grants = factory.Faker('text')

  # budget info
  start_year = factory.LazyAttribute(lambda o: random.randrange(1980, 2016))
  budget_last = factory.LazyAttribute(lambda o: random.randrange(1000, 800000))
  budget_current = factory.LazyAttribute(lambda o: random.randrange(1000, 800000))

  # this grant info
  grant_request = factory.Faker('text')
  contact_person = factory.Faker('name')
  contact_person_title = factory.Faker('prefix')
  grant_period = factory.Faker('text')
  amount_requested = factory.LazyAttribute(lambda o: random.choice([10000, 100000]))

  support_type = 'General support'
  # TODO
  # support_type = factory.LazyAttribute(lambda o: random.choice(['General support', 'Project support'])
  # project_title = 
  # project_budget = 

  # fiscal sponsor
  # fiscal_org = 
  # fiscal_person = 
  # fiscal_telephone = 
  # fiscal_email = 
  # fiscal_address = 
  # fiscal_city = 
  # fiscal_state = 
  # fiscal_zip =

  narrative1 = factory.Faker('paragraph')
  narrative2 = factory.Faker('paragraph') 
  narrative3 = factory.Faker('paragraph')
  narrative4 = factory.Faker('paragraph')
  narrative5 = factory.Faker('paragraph')
  narrative6 = factory.Faker('paragraph')

  # TODO
  # cycle_question = 

  timeline = '[]'

  # collab references (after narrative 5)
  collab_ref1_name = factory.Faker('name')
  collab_ref1_org = factory.Faker('company')
  collab_ref1_phone = factory.Faker('phone_number')
  collab_ref1_email = factory.Faker('email')
  collab_ref2_name = factory.Faker('name')
  collab_ref2_org = factory.Faker('company')
  collab_ref2_phone = factory.Faker('phone_number')
  collab_ref2_email = factory.Faker('email')

  # racial justice references (after narrative 6)
  # racial_justice_ref1_name = 
  # racial_justice_ref1_org = 
  # racial_justice_ref1_phone = 
  # racial_justice_ref1_email = 

  # racial_justice_ref2_name = 
  # racial_justice_ref2_org = 
  # racial_justice_ref2_phone = 
  # racial_justice_ref2_email = 

  # files
  budget = factory.Faker('sha256')
  demographics = factory.Faker('sha256')
  funding_sources = factory.Faker('sha256')
  budget1 = factory.Faker('sha256')
  budget2 = factory.Faker('sha256')
  budget3 = factory.Faker('sha256')
  project_budget_file = factory.Faker('sha256')
  # fiscal_letter = 

  # admin fields
  # pre_screening_status = 
  # giving_projects = 
  # scoring_bonus_poc = 
  # scoring_bonus_geo = 
  # site_visit_report = 
