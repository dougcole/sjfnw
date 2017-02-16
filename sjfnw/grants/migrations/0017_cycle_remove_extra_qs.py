# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0016_cycle_questions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='grantcycle',
            name='extra_question',
        ),
        migrations.RemoveField(
            model_name='grantcycle',
            name='two_year_grants',
        ),
        migrations.RemoveField(
            model_name='grantcycle',
            name='two_year_question',
        ),
    ]
