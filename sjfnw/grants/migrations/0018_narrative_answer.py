# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0017_cycle_remove_extra_qs'),
    ]

    operations = [
        migrations.CreateModel(
            name='NarrativeAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('cycle_narrative', models.ForeignKey(to='grants.CycleNarrative')),
                ('grant_application', models.ForeignKey(to='grants.GrantApplication')),
            ],
        ),
        migrations.AddField(
            model_name='grantapplication',
            name='narratives',
            field=models.ManyToManyField(to='grants.CycleNarrative', through='grants.NarrativeAnswer'),
        ),
    ]
