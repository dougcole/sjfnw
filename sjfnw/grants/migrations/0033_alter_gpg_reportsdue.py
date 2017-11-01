# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0032_alter_reportquestion_orderby'),
    ]

    operations = [
        migrations.RenameField(
            model_name='givingprojectgrant',
            old_name='first_yer_due',
            new_name='first_report_due'
        ),
        migrations.AlterField(
            model_name='givingprojectgrant',
            name='first_report_due',
            field=models.DateField(verbose_name=b'First grantee report due date'),
        ),
        migrations.AddField(
            model_name='givingprojectgrant',
            name='second_report_due',
            field=models.DateField(null=True, verbose_name=b'Second grantee report due date (if applicable)', blank=True),
        ),
    ]
