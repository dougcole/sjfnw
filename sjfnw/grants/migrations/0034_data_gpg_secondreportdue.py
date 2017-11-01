# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_second_date(apps, schema_editor):
  GivingProjectGrant = apps.get_model('grants', 'GivingProjectGrant')
  grants = GivingProjectGrant.objects.filter(second_amount__isnull=False)
  for grant in grants:
    second_date = grant.first_report_due.replace(year=grant.first_report_due.year + 1)
    grant.second_report_due=second_date
    grant.save()

def remove_second_date(apps, schema_editor):
  GivingProjectGrant = apps.get_model('grants', 'GivingProjectGrant')
  GivingProjectGrant.objects.update(second_report_due=None)

class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0033_alter_gpg_reportsdue'),
    ]

    operations = [
        migrations.RunPython(add_second_date, remove_second_date)
    ]
