# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0036_alter_cyclereportquestion'),
    ]

    operations = [
        migrations.AddField(
            model_name='granteereport',
            name='visible',
            field=models.BooleanField(default=False, help_text=b'Check this to make the report visible to members of the GP that made the grant. (When unchecked, report is only visible to staff and the org that submitted it.)'),
        ),
        migrations.AlterUniqueTogether(
            name='cyclereportquestion',
            unique_together=set([('grant_cycle', 'order')]),
        ),
    ]
