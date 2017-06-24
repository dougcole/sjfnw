# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0028_help_text_updates'),
    ]

    operations = [
        migrations.CreateModel(
            name='CycleReportQuestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('grant_cycle', models.ForeignKey(to='grants.GrantCycle')),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='GranteeReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('giving_project_grant', models.ForeignKey(to='grants.GivingProjectGrant')),
            ],
        ),
        migrations.CreateModel(
            name='ReportAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('cycle_report_question', models.ForeignKey(to='grants.CycleReportQuestion')),
                ('grantee_report', models.ForeignKey(to='grants.GranteeReport')),
            ],
        ),
        migrations.CreateModel(
            name='ReportQuestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, blank=True)),
                ('name', models.CharField(help_text=b'Short description of question topic, e.g. "mission", "racial_justice"', max_length=75)),
                ('version', models.CharField(help_text=b'Short description of this variation of the question, e.g. "standard" for general SJF use, "rapid" for rapid response cycles.', max_length=40)),
                ('text', models.TextField(help_text=b"Question text to display, in raw html. Don't include question number - that will be added automatically")),
                ('word_limit', models.PositiveSmallIntegerField(default=750, help_text=b'Word limit for the question')),
                ('archived', models.DateField(null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='granteereport',
            name='report_answers',
            field=models.ManyToManyField(to='grants.CycleReportQuestion', through='grants.ReportAnswer'),
        ),
        migrations.AddField(
            model_name='cyclereportquestion',
            name='report_question',
            field=models.ForeignKey(to='grants.ReportQuestion'),
        ),
        migrations.AddField(
            model_name='grantcycle',
            name='report_questions',
            field=models.ManyToManyField(to='grants.ReportQuestion', through='grants.CycleReportQuestion'),
        ),
        migrations.AlterUniqueTogether(
            name='reportanswer',
            unique_together=set([('grantee_report', 'cycle_report_question')]),
        ),
        migrations.AlterUniqueTogether(
            name='cyclereportquestion',
            unique_together=set([('grant_cycle', 'report_question')]),
        ),
    ]
