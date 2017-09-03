import random

import factory

from faker import Faker
from pytz import utc

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

  title = factory.Iterator(
    GP_NAMES, getter=lambda n: '{} Giving Project'.format(n)
  )

  fundraising_training = factory.LazyAttribute(
    lambda o: fake.date_time_this_year(before_now=o.post_training, tzinfo=utc)
  )
  fundraising_deadline = factory.LazyAttribute(
    lambda o: fake.date_time_this_year(before_now=o.post_deadline, tzinfo=utc)
  )

  fund_goal = factory.LazyFunction(lambda: random.randint(5000, 50000))
