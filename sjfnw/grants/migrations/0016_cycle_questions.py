# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from sjfnw.grants.constants import STANDARD_NARRATIVES, TWO_YEAR_GRANT_QUESTION

def get_questions(cycle):
  if cycle.title == 'Displaced Tenants Fund':
    return [
      {'name': 'describe_mission', 'version': 'standard'},
      {'name': 'most_impacted', 'version': 'tenants'},
      {'name': 'root_causes', 'version': 'tenants'},
      {'name': 'workplan', 'version': 'tenants'},
      {'name': 'timeline', 'version': 'year'},
      {'name': 'racial_justice', 'version': 'tenants'},
      {'name': 'collaboration', 'version': 'tenants'}
    ]
  elif cycle.title == 'EPIC Zero Detention Project':
    return [
      {'name': 'describe_mission', 'version': 'standard'},
      {'name': 'most_impacted', 'version': 'epic'},
      {'name': 'root_causes', 'version': 'epic'},
      {'name': 'workplan', 'version': 'epic'},
      {'name': 'timeline', 'version': 'year'},
      {'name': 'racial_justice', 'version': 'epic'},
      {'name': 'collaboration', 'version': 'epic'}
    ]
  else:
    return STANDARD_NARRATIVES

def set_cycle_questions(apps, schema_editor):
  NarrativeQuestion = apps.get_model('grants', 'NarrativeQuestion')
  GrantCycle = apps.get_model('grants', 'GrantCycle')
  CycleNarrative = apps.get_model('grants', 'CycleNarrative')
  standard_two_year = NarrativeQuestion.objects.get(**TWO_YEAR_GRANT_QUESTION)

  for cycle in GrantCycle.objects.all():

    questions = get_questions(cycle)
    for i, q in enumerate(questions):
      order = i + 1
      if cycle.two_year_grants and i >= 4:
        order = order + 1

      question = NarrativeQuestion.objects.get(**q)

      cn = CycleNarrative(narrative_question=question, grant_cycle=cycle, order=order)
      cn.save()

    if cycle.two_year_grants:
      question = standard_two_year
      if cycle.two_year_question != standard_two_year.text:
        question = NarrativeQuestion(
          name=TWO_YEAR_GRANT_QUESTION['name'], version=str(cycle.pk),
          text=cycle.two_year_question, archived=cycle.close.date
        )
        question.save()

      cn = CycleNarrative(narrative_question=question, grant_cycle=cycle, order=4)
      cn.save()

    if cycle.extra_question:
      question = NarrativeQuestion(
        name='cycle_question', version=str(cycle.pk),
        text=cycle.extra_question, archived=cycle.close.date
      )
      question.save()
      order = len(questions) + (1 if cycle.two_year_grants else 0)
      cn = CycleNarrative(narrative_question=question, grant_cycle=cycle, order=order)
      cn.save()

def remove_cycle_questions(apps, schema_editor):
  CycleNarrative = apps.get_model('grants', 'CycleNarrative')
  CycleNarrative.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0015_data_narrative_qs'),
    ]

    operations = [
        migrations.RunPython(set_cycle_questions, reverse_code=remove_cycle_questions)
    ]
