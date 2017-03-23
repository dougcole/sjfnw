# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

""" Create NarrativeQuestion instances for Seed & Rapid Response cycles """

QUESTIONS = [
  {
    'name': 'group_beliefs',
    'version': 'seed',
    'text': 'Why was your group founded and what do you believe in?',
    'word_limit': 300
  },
  {
    'name': 'most_impacted',
    'version': 'seed',
    'text': 'What problems, needs or issues does your work address? What communities are most impacted by these issues? How are those communities involved in your organization? If the communities most impacted are not currently involved, please explain how you are working towards their involvement and leadership.',
    'word_limit': 400
  },
  {
    'name': 'workplan',
    'version': 'seed',
    'text': 'If you get this grant, what will the funds be used for? List goals and specific activities/strategies for your work over the next year.',
    'word_limit': 300
  },
  {
    'name': 'resources',
    'version': 'seed',
    'text': 'New groups do so much, often without any money. Tell us about how you get your work done? What resources does it take (volunteer time, donations of space, food, etc)? What are some of your typical expenses? Where has the money and resources come from?',
    'word_limit': 400
  },
  {
    'name': 'collaboration',
    'version': 'seed',
    'text': 'Are you partnering or collaborating with other groups? If so, please tell us which groups you are collaborating with and how those relationships are helping your group get established.',
    'word_limit': 250
  },
  {
    'name': 'most_impacted',
    'version': 'rapid',
    'text': 'What emerging problems, needs or issues will your rapid response project address? What communities are most impacted by these issues? How are those communities involved in your organization and this project?',
    'word_limit': 400
  },
  {
    'name': 'workplan',
    'version': 'rapid',
    'text': 'Tell us about your project. What do you plan to do? What will the funds be used for? Please be specific.',
    'word_limit': 300
  },
  {
    'name': 'why_rapid',
    'version': 'rapid',
    'text': 'Why does this project require a rapid response? Please tell us why it wasn\'t possible to plan ahead for this project.',
    'word_limit': 300
  },
  {
    'name': 'collaboration',
    'version': 'rapid',
    'text': 'Are you partnering or collaborating with other groups on this project? If so, please tell us which groups or organizations you are collaborating with and why.',
    'word_limit': 250
  },
  {
    'name': 'expedited',
    'version': 'rapid',
    'text': 'Does this request need an expedited review? If so, what is the ideal date by when you need to be notified?',
    'word_limit': 50
  }
]

def create_questions(apps, schema_editor):
  NarrativeQuestion = apps.get_model('grants', 'NarrativeQuestion')
  for q in QUESTIONS:
    question =  NarrativeQuestion(**q)
    question.save()

def delete_questions(apps, schema_editor):
  NarrativeQuestion = apps.get_model('grants', 'NarrativeQuestion')
  NarrativeQuestion.objects.filter(version__in=['rapid', 'seed']).delete()

class Migration(migrations.Migration):

    dependencies = [
      ('grants', '0020_remove_narrative_fields'),
    ]

    operations = [
      migrations.RunPython(create_questions, reverse_code=delete_questions)
    ]
