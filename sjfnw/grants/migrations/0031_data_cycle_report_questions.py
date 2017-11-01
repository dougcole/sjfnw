# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from sjfnw.grants.constants import STANDARD_REPORT_QUESTIONS, RAPID_REPORT_QUESTIONS

""" Adds default set of report_questions to all existing cycles """

# model methods aren't available in migrations, so recreate cycle.get_type()
def get_cycle_type(cycle):
  if 'Rapid Response' in cycle.title:
    return 'rapid'
  elif 'Seed' in cycle.title:
    return 'seed'
  return 'standard'

def add_default_questions(apps, schema_editor):
  GrantCycle = apps.get_model('grants', 'GrantCycle')
  ReportQuestion = apps.get_model('grants', 'ReportQuestion')
  CycleReportQuestion = apps.get_model('grants', 'CycleReportQuestion')
  cycles = GrantCycle.objects.all().prefetch_related('report_questions')
  standard_questions = [
    ReportQuestion.objects.get(name=q['name'], version=q['version']) for q in STANDARD_REPORT_QUESTIONS
  ]
  rapid_questions = [
    ReportQuestion.objects.get(name=q['name'], version=q['version']) for q in RAPID_REPORT_QUESTIONS
  ]
  for cycle in cycles:
    cycle_type = get_cycle_type(cycle)
    if cycle_type == 'seed' or cycle.report_questions.count() != 0:
      continue

    if cycle_type == 'standard':
      question_set = STANDARD_REPORT_QUESTIONS
      questions = standard_questions
      print('Adding standard report questions to cycle {}: {}'.format(
        cycle.pk, cycle.title))
    else:
      question_set = RAPID_REPORT_QUESTIONS
      questions = rapid_questions
      print('Adding rapid response report questions to cycle {}: {}'.format(
        cycle.pk, cycle.title))

    for i, question in enumerate(questions):
      crq = CycleReportQuestion(grant_cycle=cycle, report_question=question, order=i + 1)
      if 'required' in question_set[i]:
        crq.required = question_set[i]['required']
      crq.save()

def remove_questions(apps, schema_editor):
  CycleReportQuestion = apps.get_model('grants', 'CycleReportQuestion')
  CycleReportQuestion.objects.all().delete()

class Migration(migrations.Migration):

  dependencies = [
    ('grants', '0030_data_grantee_reports'),
  ]

  operations = [
    migrations.RunPython(add_default_questions, remove_questions)
  ]
