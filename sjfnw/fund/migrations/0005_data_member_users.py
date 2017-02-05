# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from django.db import migrations


def set_users(apps, schema_editor):
    """ Set user_id field on members by matching email to username """
    Member = apps.get_model("fund", "Member")
    User = apps.get_model("auth", "User")

    users = dict(User.objects.values_list('username', 'id'))

    for member in Member.objects.all():
      if not member.email:
        raise Exception('\nMember {} {} has no email'.format(member.first_name, member.last_name))
      elif member.email in users:
        member.user_id = users[member.email]
        member.save()
      else:
        raise Exception('\nNo user with username of {}'.format(member.email))

def unset_users(apps, schema_editor):
    Member = apps.get_model("fund", "Member")
    # re-populate email if it's missing
    for member in Member.objects.filter(email=''):
      member.email = member.user.username
      member.save()
    Member.objects.all().update(user_id=None)

class Migration(migrations.Migration):

    dependencies = [
        ('fund', '0004_member_add_user_field'),
    ]

    operations = [
        migrations.RunPython(set_users, reverse_code=unset_users)
    ]
