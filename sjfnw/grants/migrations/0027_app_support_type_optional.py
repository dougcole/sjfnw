# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0026_question_archived_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grantapplication',
            name='support_type',
            field=models.CharField(blank=True, max_length=50, choices=[(b'General support', b'General'), (b'Project support', b'Project')]),
        ),
    ]
