# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0034_data_gpg_secondreportdue'),
    ]

    operations = [
        migrations.AddField(
            model_name='granteereportdraft',
            name='files',
            field=models.TextField(default=b'{}'),
        ),
        migrations.AlterField(
            model_name='reportquestion',
            name='input_type',
            field=models.CharField(default=b'text', help_text=b'Select the type of for input to use for this question.', max_length=20, choices=[(b'text', b'Text box'), (b'short_text', b'Single-line text input'), (b'number', b'Number'), (b'photo', b'Photo upload'), (b'file', b'File upload')]),
        ),
    ]
