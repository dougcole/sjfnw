# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0019_data_narrative_answers'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='grantapplicationoverflow',
            name='grant_application',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='cycle_question',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='narrative1',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='narrative2',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='narrative3',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='narrative4',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='narrative5',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='narrative6',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='timeline',
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='narratives',
            field=models.ManyToManyField(to='grants.CycleNarrative', through='grants.NarrativeAnswer', blank=True),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='support_type',
            field=models.CharField(default=b'General support', max_length=50, choices=[(b'General support', b'General'), (b'Project support', b'Project')]),
        ),
        migrations.DeleteModel(
            name='GrantApplicationOverflow',
        ),
    ]
