from datetime import timedelta
import json, logging

from django.core.urlresolvers import reverse
from django.utils import timezone

from sjfnw.fund import models
from sjfnw.fund.tests.base import BaseFundTestCase

logger = logging.getLogger('sjfnw')

class GPSurveys(BaseFundTestCase):

  url = reverse('fund:home')
  template = 'fund/forms/gp_survey.html'

  def _create_survey(self):
    """ Utility method for other tests. Create survey and connect it to GP 1 """
    survey = models.Survey(
      title='Basic Survey',
      intro=('Please fill out this quick survey evaluating our last meeting.'
             ' Responses are completely anonymous. Once you have completed '
             'it, you\'ll be taken to your regular home page.'),
      questions=(
        '[{"question": "How well did we meet our goals? (1 = did not meet, 5 = met all our goals)",'
        ' "choices": [1, 2, 3, 4, 5]}, '
        '{"question": "Any other comments for us?", "choices": []}]'))
    survey.save()
    gp_survey = models.GPSurvey(survey=survey, giving_project_id=1, date=timezone.now())
    gp_survey.save()
    self.gps_pk = gp_survey.pk

  def test_creation(self):
    self.login_as_admin()
    form_data = {
     'title': 'Another Survey',
     'intro': 'Please fill this out!',
     'questions_0': 'What is love?',
     'questions_1': 'Baby don\'t',
     'questions_2': 'No more',
     'questions_3': '',
     'questions_4': '',
     'questions_5': '',
     'questions_6': 'What\'s love got to do with it?',
     'questions_7': '',
     'questions_8': '',
     'questions_9': '',
     'questions_10': '',
     'questions_11': ''
    }
    res = self.client.post('/admin/fund/survey/add/', form_data)

    survey = models.Survey.objects.get(title='Another Survey')
    self.assertEqual(survey.intro, 'Please fill this out!')

    # connect it to GP 1
    gp_survey = models.GPSurvey(survey=survey, giving_project_id=1, date=timezone.now())
    gp_survey.save()

    # log into PC and verify it displays as expected
    self.login_as_member('first')

    res = self.client.get(self.url, follow=True)

    self.assertTemplateUsed(res, self.template)
    self.assertContains(res, form_data['intro'])
    self.assertContains(res, '<form id="gp-survey"', count=1)
    self.assertContains(res, '<textarea', count=1)

  def test_fill(self):
    self._create_survey()
    self.login_as_member('first')

    membership = models.Membership.objects.get(pk=self.ship_id)
    self.assertEqual(membership.completed_surveys, '[]')

    res = self.client.get(self.url, follow=True)
    self.assertTemplateUsed(res, self.template)
    self.assert_count(models.SurveyResponse.objects, 0)

    # Post a survey response
    form_data = {
        'responses_0': '2',
        'responses_1': 'No comments.',
        'date': timezone.now().date,
        'gp_survey': self.gps_pk
    }
    post_url = reverse('fund:project_survey', kwargs={'gp_survey_id': self.gps_pk})
    res = self.client.post(post_url, form_data)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.content, 'success')

    new_response = models.SurveyResponse.objects.get(gp_survey_id=self.gps_pk)
    self.assertEqual(new_response.responses, json.dumps(
      ["How well did we meet our goals? (1 = did not meet, 5 = met all our goals)", "2",
       "Any other comments for us?", "No comments."]))

  def test_future_survey(self):
    self._create_survey()
    self.login_as_member('first')

    gp_survey = models.GPSurvey.objects.get(giving_project_id=1)
    gp_survey.date = timezone.now() + timedelta(days=20)
    gp_survey.save()

    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/home.html')
    self.assertTemplateNotUsed(res, self.template)

  def test_completed_survey(self):
    self._create_survey()
    self.login_as_member('first')

    # mark the survey complete
    membership = models.Membership.objects.get(pk=self.ship_id)
    membership.completed_surveys = '[1]'
    membership.save()

    res = self.client.get(self.url)
    self.assertEqual(res.status_code, 200)
    self.assertTemplateUsed(res, 'fund/home.html')
    self.assertTemplateNotUsed(res, self.template)

  def test_load_not_found(self):
    self.login_as_member('first')

    url = reverse('fund:project_survey', kwargs={'gp_survey_id': '9999'})
    res = self.client.get(url)

    self.assertEqual(res.status_code, 404)
