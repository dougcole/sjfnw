import datetime
import random

import factory
from faker import Faker

class User(factory.django.DjangoModelFactory):

  class Meta:
    model = 'auth.User'

  username = factory.Faker('email')
  email = factory.SelfAttribute('username')

  @factory.post_generation
  def add_password(self, create, *args, **kwargs):
    if not create:
      return
    self.set_password(self.password or 'password')
