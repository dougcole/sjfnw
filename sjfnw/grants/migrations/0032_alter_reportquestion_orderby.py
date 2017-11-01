# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0031_data_cycle_report_questions'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reportquestion',
            options={'ordering': ('name', 'version')},
        ),
    ]
