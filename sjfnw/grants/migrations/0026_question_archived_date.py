# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0025_narrative_answer_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='narrativequestion',
            name='archived',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='narrativequestion',
            unique_together=set([]),
        ),
    ]
