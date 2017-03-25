# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0024_cycle_amount_note'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='narrativeanswer',
            unique_together=set([('grant_application', 'cycle_narrative')]),
        ),
    ]
