# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import sjfnw.grants.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0013_org_user_blank'),
    ]

    operations = [
        migrations.CreateModel(
            name='CycleNarrative',
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
            name='NarrativeQuestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, blank=True)),
                ('name', models.CharField(help_text=b'Short description of question topic, e.g. "mission", "racial_justice"', max_length=75)),
                ('version', models.CharField(help_text=b'Short description of this variation of the question, e.g. "standard" for general SJF use, "rapid" for rapid response cycles.', max_length=40)),
                ('text', models.TextField(help_text=b"Text to display, in raw html. Don't include question number - that will be added automatically")),
                ('word_limit', models.PositiveSmallIntegerField(help_text=b'Word limit for the question. If left blank, no word limit will be enforced', null=True, blank=True)),
                ('archived', models.DateField(help_text=b"Archived questions remain associated with existing grant cycles but can't be added to new grant cycles.", null=True, blank=True)),
            ],
        ),
        migrations.AlterField(
            model_name='grantapplication',
            name='narrative6',
            field=models.TextField(help_text=b"Your organization's leadership body is the group of people who together make strategic decisions about the organization's direction, provide oversight and guidance, and are ultimately responsible for the organization's mission and ability to carry out its mission. In most cases, this will be a Board of Directors, but it might also be a steering committee, collective, or other leadership structure.", verbose_name=b'<p>Social Justice Fund prioritizes groups working on racial justice, especially those making connections between racism, economic injustice, homophobia, and other forms of oppression. Tell us how your organization is working toward racial justice and how you are drawing connections to economic injustice, homophobia, and other forms of oppression. While we believe people of color must lead the struggle for racial justice, we also realize that the demographics of our region make the work of white anti-racist allies critical to achieving racial justice. If your organization\'s <span class="has-more-info" id="nar-6">leadership body</span> is majority white, also describe how you work as an ally to communities of color. Be as specific as possible, and list at least one organization led by people of color that we can contact as a reference for your racial justice work. Include their name, organization, phone number and email.</p><p><i>Please make sure you have asked permission to list someone as a racial justice reference before submitting their contact information. Your racial justice reference cannot be a representative from your organization. We define "led by people of color" to mean that more that 51% or more of the organizations leadership body (ie. board of directors or other leadership model) are people of color. If your organization is majority people of color led, leave the references blank.</i></p>', validators=[sjfnw.grants.models.WordLimitValidator(450)]),
        ),
        migrations.AlterUniqueTogether(
            name='narrativequestion',
            unique_together=set([('name', 'version')]),
        ),
        migrations.AddField(
            model_name='cyclenarrative',
            name='narrative_question',
            field=models.ForeignKey(to='grants.NarrativeQuestion'),
        ),
        migrations.AddField(
            model_name='grantcycle',
            name='narrative_questions',
            field=models.ManyToManyField(to='grants.NarrativeQuestion', through='grants.CycleNarrative'),
        ),
        migrations.AlterUniqueTogether(
            name='cyclenarrative',
            unique_together=set([('grant_cycle', 'narrative_question')]),
        ),
    ]
