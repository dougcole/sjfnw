# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0023_app_files_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='grantcycle',
            name='amount_note',
            field=models.CharField(help_text=b'Text to display in parenthesis after "Amount Requested" in the grant application form', max_length=255, blank=True),
        ),
    ]
