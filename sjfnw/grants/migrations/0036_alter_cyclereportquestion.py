# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0035_alter_granteereportdraft'),
    ]

    operations = [
        migrations.AddField(
            model_name='cyclereportquestion',
            name='required',
            field=models.BooleanField(default=True),
        ),
    ]
