# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import sys

from django.db import models, migrations

narratives = {
  'describe_mission': 'narrative1',
  'most_impacted': 'narrative2',
  'root_causes': 'narrative3',
  'workplan': 'narrative4',
  'collaboration': 'narrative5',
  'racial_justice': 'narrative6',
  'cycle_question': 'cycle_question',
  'two_year_grant': 'two_year_question',
  'timeline': 'timeline',
  'racial_justice_references': 'racial_justice_ref',
  'collaboration_references': 'collab_ref'
}

def convert_references(app, prefix):
  value = []
  for i in [1, 2]:
    value.append({
      'name': getattr(app, '{}{}_name'.format(prefix, i)),
      'org': getattr(app, '{}{}_org'.format(prefix, i)),
      'phone': getattr(app, '{}{}_phone'.format(prefix, i)),
      'email': getattr(app, '{}{}_email'.format(prefix, i)),
    })
  return json.dumps(value)

def create_answers(apps, schema_editor):
  NarrativeAnswer = apps.get_model('grants', 'NarrativeAnswer')
  GrantApplication = apps.get_model('grants', 'GrantApplication')
  CycleNarrative = apps.get_model('grants', 'CycleNarrative')

  for app in GrantApplication.objects.all():
    cycle_narratives = (CycleNarrative.objects
        .select_related('narrative_question')
        .filter(grant_cycle_id=app.grant_cycle_id))
    for cn in cycle_narratives:
      field_name = narratives[cn.narrative_question.name]
      if field_name.endswith('_ref'):
        content = convert_references(app, field_name)
      elif field_name == 'two_year_question':
        if hasattr(app, 'overflow'):
          content = getattr(app.overflow, field_name)
        else:
          sys.stdout.write('\nWARN: App missing two_year_question answer {}'.format(app))
          content = ''
      else:
        content = getattr(app, field_name)

      answer = NarrativeAnswer(grant_application=app, cycle_narrative=cn, text=content)
      answer.save()

def delete_answers(apps, schema_editor):
  NarrativeAnswer = apps.get_model('grants', 'NarrativeAnswer')
  NarrativeAnswer.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0018_narrative_answer'),
    ]

    operations = [
      migrations.RunPython(create_answers, reverse_code=delete_answers)
    ]
