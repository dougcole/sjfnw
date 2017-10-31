# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

""" Creates initial ReportQuestions """

REPORT_QUESTIONS = [
  {
    'name': 'contact_info',
    'version': 'legacy',
    'text': 'Contact person for this report - name, title, phone number, email, website',
    'word_limit': 500
  }, {
    'name': 'summarize_last_year',
    'version': 'legacy',
    'text': 'Thinking about the Giving Project volunteers who decided to fund you last year, including those you met on your site visit, what would you like to tell them about what you\'ve done over the last year?',
    'word_limit': 500
  }, {
    'name': 'goal_progress',
    'version': 'legacy',
    'text': 'Please refer back to your application from last year. Looking at the goals you outlined in your application, what progress have you made on each? If you were unable to achieve those goals or changed your direction, please explain why.',
    'word_limit': 500
  }, {
    'name': 'quantitative_measures',
    'version': 'legacy',
    'text': 'Do you evaluate your work by any quantitative measures (e.g., number of voters registered, members trained, leaders developed, etc.)? If so, provide that information:',
    'word_limit': 500
  }, {
    'name': 'evaluation',
    'version': 'legacy',
    'text': 'What other type of evaluations do you use internally? Please share any outcomes that are relevant to the work funded by this grant.',
    'word_limit': 500
  }, {
    'name': 'achievements',
    'version': 'legacy',
    'text': 'What specific victories, benchmarks, and/or policy changes (local, state, regional, or national) have you achieved over the past year?',
    'word_limit': 500
  }, {
    'name': 'collaboration',
    'version': 'legacy',
    'text': 'What other organizations did you work with to achieve those accomplishments?',
    'word_limit': 500
  }, {
    'name': 'new_funding',
    'version': 'legacy',
    'text': 'Did your grant from Social Justice Fund help you access any new sources of funding? If so, please explain.',
    'word_limit': 500
  }, {
    'name': 'organizational_changes',
    'version': 'legacy',
    'text': 'Describe any major staff or board changes or other major organizational changes in the past year.',
    'word_limit': 500
  }, {
    'name': 'total_size',
    'version': 'legacy',
    'text': 'What is the total size of your base? That is, how many people, including paid staff, identify as part of your organization?',
    'word_limit': 100,
    'input_type': 'short_text'
  }, {
    'name': 'donations_count',
    'version': 'legacy',
    'text': 'How many individuals gave a financial contribution of any size to your organization in the last year?',
    'word_limit': 100,
    'input_type': 'short_text'
  }, {
    'name': 'donations_count_prev',
    'version': 'legacy',
    'text': 'How many individuals made a financial contribution the previous year?',
    'word_limit': 100,
    'input_type': 'short_text'
  }, {
    'name': 'stay_informed',
    'version': 'legacy',
    'text': 'What is the best way for us to stay informed about your work? (Enter any/all that apply)',
    'word_limit': 500,
  }, {
    'name': 'other_comments',
    'version': 'legacy',
    'text': 'Other comments or information? Do you have any suggestions for how SJF can improve its grantmaking programs?',
    'word_limit': 500
  }, {
    'name': 'photo1',
    'version': 'legacy',
    'text': 'Please provide two or more photos that show your organization\'s members, activities, etc. These pictures help us tell the story of our grantees and of Social Justice Fund to the broader public.',
    'word_limit': 0,
    'input_type': 'photo'
  }, {
    'name': 'photo2',
    'version': 'legacy',
    'text': '',
    'word_limit': 0,
    'input_type': 'photo'
  }, {
    'name': 'photo3',
    'version': 'legacy',
    'text': '',
    'word_limit': 0,
    'input_type': 'photo'
  }, {
    'name': 'photo4',
    'version': 'legacy',
    'text': '',
    'word_limit': 0,
    'input_type': 'photo'
  }, {
    'name': 'photo_release',
    'version': 'general',
    'text': 'Photo release form',
    'input_type': 'file'
  }, {
    'name': 'progress',
    'version': 'rapid_response',
    'text': 'Please refer back to your Rapid Response application. Looking at the project goals you outlined in your application, what progress have you made on each? If you were unable to achieve those goals or changed your direction, please explain why.',
    'input_type': 'text'
  }, {
    'name': 'impact',
    'version': 'rapid_response',
    'text': 'What was the impact of your rapid response activities? Please include any specific victories, benchmarks, and/or policy changes (local, state, regional, or national) you achieved as well as qualitative impacts and learnings from your work.',
    'input_type': 'text'
  }, {
    'name': 'current_direction',
    'version': 'rapid_response',
    'text': 'Now that this project has concluded, what direction is the work going in? This is not meant to be exhaustive or overly detailed, this can be as simple as a few bullet points about the direction of the work.',
    'input_type': 'text'
  }, {
    'name': 'relation_to_regular_work',
    'version': 'rapid_response',
    'text': 'How do your rapid response activities relate to or impact your regular ongoing work?',
    'input_type': 'text'
  }, {
    'name': 'more_info_for_members',
    'version': 'rapid_response',
    'text': 'Is there anything else you like SJF members to know about what you\'ve done with the Rapid Response funding you received or the impact this grant had on your work?',
    'input_type': 'text'
  }, {
    'name': 'photo',
    'version': 'rapid_response',
    'text': 'Do you have a photo from your Rapid Response project? If so please upload a photo along with a photo Release Form',
    'input_type': 'photo'
  }
]

def create_questions(apps, schema_editor):
  ReportQuestion = apps.get_model('grants', 'ReportQuestion')
  for q in REPORT_QUESTIONS:
    question = ReportQuestion(**q)
    question.save()

def delete_questions(apps, schema_editor):
  ReportQuestion = apps.get_model('grants', 'ReportQuestion')
  ReportQuestion.objects.all().delete()

class Migration(migrations.Migration):

  dependencies = [
    ('grants', '0029_add_grantee_report'),
  ]

  operations = [
    migrations.RunPython(create_questions, delete_questions)
  ]
