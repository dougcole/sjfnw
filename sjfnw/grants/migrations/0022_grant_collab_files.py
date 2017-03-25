# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sjfnw.grants.models


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0021_data_rapid_seed_questions'),
    ]

    reversible = False # collaboration fields will be lost

    operations = [
        migrations.AlterModelOptions(
            name='narrativequestion',
            options={'ordering': ('name', 'version')},
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref1_email',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref1_name',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref1_org',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref1_phone',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref2_email',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref2_name',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref2_org',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='collab_ref2_phone',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref1_email',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref1_name',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref1_org',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref1_phone',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref2_email',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref2_name',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref2_org',
        ),
        migrations.RemoveField(
            model_name='grantapplication',
            name='racial_justice_ref2_phone',
        ),
        migrations.AlterField(
            model_name='draftgrantapplication',
            name='budget1',
            field=sjfnw.grants.models.BasicFileField(upload_to=b'/', max_length=255, verbose_name=b'Annual statement'),
        ),
        migrations.AlterField(
            model_name='draftgrantapplication',
            name='budget2',
            field=sjfnw.grants.models.BasicFileField(upload_to=b'/', max_length=255, verbose_name=b'Annual operating budget'),
        ),
        migrations.AlterField(
            model_name='draftgrantapplication',
            name='budget3',
            field=sjfnw.grants.models.BasicFileField(upload_to=b'/', max_length=255, verbose_name=b'Balance sheet'),
        ),
        migrations.AlterField(
            model_name='draftgrantapplication',
            name='demographics',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/'),
        ),
        migrations.AlterField(
            model_name='draftgrantapplication',
            name='fiscal_letter',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/'),
        ),
        migrations.AlterField(
            model_name='draftgrantapplication',
            name='funding_sources',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/'),
        ),
        migrations.AlterField(
            model_name='draftgrantapplication',
            name='project_budget_file',
            field=sjfnw.grants.models.BasicFileField(upload_to=b'/', max_length=255, verbose_name=b'Project budget'),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='budget',
            field=sjfnw.grants.models.BasicFileField(blank=True, max_length=255, upload_to=b'/', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='budget1',
            field=sjfnw.grants.models.BasicFileField(help_text=b'Statement of actual income and expenses for the most recent completed fiscal year. Upload in your own format, but do not send your annual report, tax returns, or entire audited financial statement.', upload_to=b'/', max_length=255, verbose_name=b'Annual statement', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='budget2',
            field=sjfnw.grants.models.BasicFileField(help_text=b"Projection of all known and estimated income and expenses for the current fiscal year. You may upload in your own format or use our budget form. NOTE: If your fiscal year will end within three months of this grant application deadline, please also attach your operating budget for the next fiscal year, so that we can get a more accurate sense of your organization's situation.", upload_to=b'/', max_length=255, verbose_name=b'Annual operating budget', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='budget3',
            field=sjfnw.grants.models.BasicFileField(help_text=b'This is a snapshot of your financial status at the moment: a brief, current statement of your assets, liabilities, and cash on hand. Upload in your own format.', upload_to=b'/', max_length=255, verbose_name=b'Balance sheet', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='demographics',
            field=sjfnw.grants.models.BasicFileField(upload_to=b'/', max_length=255, verbose_name=b'Diversity chart', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='fiscal_letter',
            field=sjfnw.grants.models.BasicFileField(validators=[sjfnw.grants.models.validate_file_extension], upload_to=b'/', max_length=255, blank=True, help_text=b"Letter from the sponsor stating that it agrees to act as your fiscal sponsor and supports Social Justice Fund's mission.", verbose_name=b'Fiscal sponsor letter'),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='funding_sources',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/', validators=[sjfnw.grants.models.validate_file_extension]),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='project_budget_file',
            field=sjfnw.grants.models.BasicFileField(validators=[sjfnw.grants.models.validate_file_extension], upload_to=b'/', max_length=255, blank=True, help_text=b'This is required only if you are requesting project-specific funds. Otherwise, it is optional. You may upload in your own format or use our budget form.', verbose_name=b'Project budget (if applicable)'),
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='status',
            field=models.CharField(max_length=50, choices=[(b'Tribal government', b'Federally recognized American Indian tribal government'), (b'501c3', b'501(c)3 organization as recognized by the IRS'), (b'501c4', b'501(c)4 organization as recognized by the IRS'), (b'Sponsored', b'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government'), (b'Other', b'Organized group of people without 501(c)3 or (c)4 status (you MUST call us before applying)')]),
        ),
        migrations.AlterField(
            model_name='organization',
            name='fiscal_letter',
            field=sjfnw.grants.models.BasicFileField(max_length=255, null=True, upload_to=b'/', blank=True),
        ),
        migrations.AlterField(
            model_name='organization',
            name='status',
            field=models.CharField(blank=True, max_length=50, choices=[(b'Tribal government', b'Federally recognized American Indian tribal government'), (b'501c3', b'501(c)3 organization as recognized by the IRS'), (b'501c4', b'501(c)4 organization as recognized by the IRS'), (b'Sponsored', b'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government'), (b'Other', b'Organized group of people without 501(c)3 or (c)4 status (you MUST call us before applying)')]),
        ),
        migrations.AlterField(
            model_name='yerdraft',
            name='photo1',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/', blank=True),
        ),
        migrations.AlterField(
            model_name='yerdraft',
            name='photo2',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/', blank=True),
        ),
        migrations.AlterField(
            model_name='yerdraft',
            name='photo3',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/', blank=True),
        ),
        migrations.AlterField(
            model_name='yerdraft',
            name='photo4',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/', blank=True),
        ),
        migrations.AlterField(
            model_name='yerdraft',
            name='photo_release',
            field=sjfnw.grants.models.BasicFileField(max_length=255, upload_to=b'/'),
        ),
    ]
