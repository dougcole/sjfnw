# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def set_users(apps, schema_editor):
  """ Set user_id field on organizations by matching org email to user username
      In dev mode, creates user if needed
  """
  Organization = apps.get_model("grants", "Organization")
  User = apps.get_model("auth", "User")

  users = dict(User.objects.values_list('username', 'id'))

  created_users = []
  for org in Organization.objects.all():
    if not org.email:
      print('WARN: Org {} has no email; leaving user_id blank'.format(org.name))
    elif org.email in users:
      org.user_id = users[org.email]
      org.save()
    else:
      if settings.DEBUG:
        user = User(username=org.email, password='pass',
            first_name=org.name[:29], last_name='(organization)')
        user.save()
        org.user_id = user.pk
        org.save()
        created_users.append(org.email)
      else:
        print('No user with username of {}; leaving user_id blank for {}'.format(org.email, org.name))

  if len(created_users):
    print('Created {} users: {}'.format(len(created_users), ', '.join(created_users)))

def unset_users(apps, schema_editor):
  Organization = apps.get_model("grants", "Organization")
  # re-populate email if it's missing
  for org in Organization.objects.filter(email=''):
    org.email = org.user.username
    org.save()
  Organization.objects.all().update(user_id=None)


class Migration(migrations.Migration):

  dependencies = [
    ('grants', '0010_organization_add_user')
  ]

  operations = [
    migrations.RunPython(set_users, reverse_code=unset_users)
  ]
