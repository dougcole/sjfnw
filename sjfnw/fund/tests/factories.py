import datetime
import random

import factory
from faker import Faker

from sjfnw.fund import models

fake = Faker()

GP_NAMES = [
  'Economic Justice', 'LGBTQ', 'Environmental Justice', 'Next Generation',
  'Immigration Justice', 'Gender Justice', 'Rural Justice', 'Movement Building',
  'Portland'
]
class GivingProject(factory.django.DjangoModelFactory):

  class Meta:
    model = 'fund.GivingProject'

  class Params:
    post_training = True
    post_deadline = False

  title = factory.Iterator(GP_NAMES, getter=lambda n: '{} Giving Project'.format(n))

  fundraising_training = factory.LazyAttribute(lambda o: fake.date_time_this_year(before_now=o.post_training))
  fundraising_deadline = factory.LazyAttribute(lambda o: fake.date_time_this_year(before_now=o.post_deadline))

  fund_goal = factory.LazyFunction(lambda: random.randint(5000, 50000))
