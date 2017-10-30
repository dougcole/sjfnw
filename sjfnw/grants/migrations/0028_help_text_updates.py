# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sjfnw.grants.models


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0027_app_support_type_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grantapplication',
            name='demographics',
            field=sjfnw.grants.models.BasicFileField(upload_to=b'/', max_length=255, verbose_name=b'Diversity chart', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='narrativequestion',
            name='word_limit',
            field=models.PositiveSmallIntegerField(help_text=b'Word limit for the question. Ignored for some question types, such as timeline and references. If left blank, no word limit will be enforced.', null=True, blank=True),
        ),
    ]
