# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0011_data_organization_users'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organization',
            name='email',
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='support_type',
            field=models.CharField(default=b'General support', max_length=50, choices=[(b'General support', b'General support'), (b'Project support', b'Project support')]),
        ),
    ]
