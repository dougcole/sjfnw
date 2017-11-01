# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def convert_yer_to_grantee_reports(apps, schema_editor):
  YearEndReport = apps.get_model('grants', 'YearEndReport')
  GranteeReport = apps.get_model('grants', 'GranteeReport')
  GrantCycle = apps.get_model('grants', 'GrantCycle')
  CycleReportQuestion = apps.get_model('grants', 'CycleReportQuestion')
  ReportAnswer = apps.get_model('grants', 'ReportAnswer')

  print('')
  for cycle in GrantCycle.objects.all():
    yers = YearEndReport.objects.filter(award__projectapp__application__grant_cycle=cycle)

    if len(yers) == 0:
      print('Cycle {} skipped'.format(cycle.pk))
      continue

    cycle_questions = (CycleReportQuestion.objects
      .select_related('report_question')
      .filter(grant_cycle=cycle))

    if len(cycle_questions) != 18:
      print('WARNING: Cycle {} has non-standard number of questions ({}); skipping'.format(
          cycle.pk, len(cycle_questions)))
      continue

    for yer in yers:
      grantee_report = GranteeReport(
        giving_project_grant=yer.award,
        created=yer.submitted,
        visible=yer.visible)
      grantee_report.save()
      for cq in cycle_questions:
        question_name = cq.report_question.name
        question_type = cq.report_question.input_type
        answer = ReportAnswer(cycle_report_question=cq, grantee_report=grantee_report)
        if question_name == 'contact_info':
          answer.text = '\n'.join([yer.contact_person, yer.email, yer.phone, yer.website])
        elif question_type == 'file' or question_type == 'photo':
          answer.text = getattr(yer, question_name).name
        else:
          if question_name == 'achievements':
            question_name = 'achieved'
          elif question_name == 'organizational_changes':
            question_name = 'major_changes'
          answer.text = getattr(yer, question_name) or ''
        answer.save()
      print('  Converted YER {}'.format(yer.pk))
      # TODO
      # yer.delete()
    print('Cycle {} complete'.format(cycle.pk))

def delete_grantee_reports(apps, schema_editor):
  GranteeReport = apps.get_model('grants', 'GranteeReport')
  GranteeReport.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('grants', '0037_alter_granteereport'),
    ]

    operations = [
        migrations.RunPython(convert_yer_to_grantee_reports, delete_grantee_reports)
    ]
