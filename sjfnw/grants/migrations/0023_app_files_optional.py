# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sjfnw.grants.models


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0022_grant_collab_files'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grantapplication',
            name='budget1',
            field=sjfnw.grants.models.BasicFileField(validators=[sjfnw.grants.models.validate_file_extension], upload_to=b'/', max_length=255, blank=True, help_text=b'Statement of actual income and expenses for the most recent completed fiscal year. Upload in your own format, but do not send your annual report, tax returns, or entire audited financial statement.', verbose_name=b'Annual statement'),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='budget2',
            field=sjfnw.grants.models.BasicFileField(validators=[sjfnw.grants.models.validate_file_extension], upload_to=b'/', max_length=255, blank=True, help_text=b"Projection of all known and estimated income and expenses for the current fiscal year. You may upload in your own format or use our budget form. NOTE: If your fiscal year will end within three months of this grant application deadline, please also attach your operating budget for the next fiscal year, so that we can get a more accurate sense of your organization's situation.", verbose_name=b'Annual operating budget'),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='budget3',
            field=sjfnw.grants.models.BasicFileField(validators=[sjfnw.grants.models.validate_file_extension], upload_to=b'/', max_length=255, blank=True, help_text=b'This is a snapshot of your financial status at the moment: a brief, current statement of your assets, liabilities, and cash on hand. Upload in your own format.', verbose_name=b'Balance sheet'),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='demographics',
            field=sjfnw.grants.models.BasicFileField(blank=True, upload_to=b'/', max_length=255, verbose_name=b'Diversity chart', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='funding_sources',
            field=sjfnw.grants.models.BasicFileField(blank=True, max_length=255, upload_to=b'/', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
    ]
