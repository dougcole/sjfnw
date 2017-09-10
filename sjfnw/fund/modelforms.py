import json, logging

from django.db import models
from django.forms import ModelForm, widgets, ValidationError

from sjfnw.forms import IntegerCommaField
from sjfnw.fund.models import Donor, Step, Survey, GivingProject, SurveyResponse

logger = logging.getLogger('sjfnw')

def custom_integer_field(field, **kwargs):
  if field.name == 'amount':
    kwargs['min_value'] = 0
    return IntegerCommaField(**kwargs)
  else:
    return field.formfield()

def make_custom_datefield(field):
  """
    date selector implementation from
    http://strattonbrazil.blogspot.com/2011/03/using-jquery-uis-date-picker-on-all.html
  """
  formfield = field.formfield()
  if isinstance(field, models.DateField):
    formfield.error_messages['invalid'] = 'Please enter a date in mm/dd/yyyy format.'
    formfield.widget.format = '%m/%d/%Y'
    formfield.widget.input_formats = ['%m/%d/%Y', '%m-%d-%Y', '%n/%j/%Y', '%n-%j-%Y']
    formfield.widget.attrs.update({'class': 'datePicker'})
  return formfield


class DonorEditForm(ModelForm):
  """ Edit a contact including estimate fields """
  formfield_callback = custom_integer_field

  class Meta:
    model = Donor
    fields = ('firstname', 'lastname', 'amount', 'likelihood', 'phone', 'email', 'notes')
    widgets = {'notes': widgets.Textarea(attrs={'cols': 25, 'rows': 4})}


class DonorPreForm(ModelForm):
  """ Edit a contact prior to fundraising training """

  class Meta:
    model = Donor
    fields = ('firstname', 'lastname', 'phone', 'email', 'notes')
    widgets = {'notes': widgets.Textarea(attrs={'cols': 25, 'rows': 4})}


class StepForm(ModelForm):
  """ Add a step """
  formfield_callback = make_custom_datefield

  class Meta:
    model = Step
    exclude = ('created', 'donor', 'completed', 'asked', 'promised')


class CreateQuestionsWidget(widgets.MultiWidget):
  """ Widget used by staff to create GPSurvey questions """

  template_name = 'fund/widgets/create_survey_questions.html'

  def __init__(self, attrs=None):
    _widgets = []
    for _ in range(1, 6):
      _widgets += [widgets.Textarea(attrs={'rows': 2}),
                   widgets.Textarea(attrs={'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs={'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs={'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs={'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs={'rows': 1, 'class': 'survey-choice'})]
    super(CreateQuestionsWidget, self).__init__(_widgets, attrs)

  def decompress(self, value):
    """ Take single DB value, break it up for widget display """
    if not value:
      return []
    val_list = []
    raw_survey = json.loads(value)
    for question in raw_survey:
      val_list.append(question['question'])
      count = 1
      for choice in question['choices']:
        val_list.append(choice)
        count += 1
      for _ in range(count, 6):
        val_list.append(None)
    return val_list

  def value_from_datadict(self, data, files, name):
    """ Consolidate widget data into a single value for storage

    Arguments:
      data   flat array of values from each sub-widget
      files  request.FILES
      name   name of this widget

    Returns json encoded string for questions field

    Example:
      Input (data arg):
        ['Rate the session', '1', '2', '3', '4', '5', None,
         'Did you learn anything?', 'Yes', 'No', None, None, None, None]
      Output:
      '[{"question": "Rate the session", "choices": ["1", "2", "3", "4", "5"]},
        {"question": "Did you learn anything?", "choices": ["Yes", "No"]}]'
    """

    survey = []
    for i in range(0, len(self.widgets), 6):
      val = self.widgets[i].value_from_datadict(data, files, '{}_{}'.format(name, i))
      if not val: # first blank question signifies end of survey
        break
      question = {'question': val, 'choices': []}
      for j in range(i + 1, i + 6):
        val = self.widgets[j].value_from_datadict(data, files, '{}_{}'.format(name, j))
        if val:
          question['choices'].append(val)
        else: # first blank choice signifies end of answer options for this q
          break
      survey.append(question)

    return json.dumps(survey)


class CreateSurvey(ModelForm):

  class Meta:
    model = Survey
    fields = ['title', 'intro', 'questions']
    widgets = {'questions': CreateQuestionsWidget()}

  def clean_questions(self):
    questions = self.cleaned_data['questions']
    if questions == '[]':
      raise ValidationError('Enter at least one question')
    return questions


class DisplayQuestionsWidget(widgets.MultiWidget):
  """ Display a Survey's questions to GP members """

  def __init__(self, survey, attrs=None):
    self.questions = json.loads(survey.questions)
    _widgets = []
    for question in self.questions:
      if question['choices']:
        choices = [(choice, choice) for _, choice in enumerate(question['choices'])]
        _widgets.append(widgets.RadioSelect(choices=choices))
      else:
        _widgets.append(widgets.Textarea(attrs={'class': 'survey-text'}))

    super(DisplayQuestionsWidget, self).__init__(_widgets, attrs)

  def decompress(self, value):
    """ Take single DB value, break it up for widget display """
    if value:
      val_list = json.loads(value)
      return_list = []
      for i in range(1, len(val_list), 2):
        return_list.append(val_list[i])
      return return_list
    else:
      return [None for _ in self.widgets]

  def format_output(self, rendered_widgets):
    """ Format widgets for display by wrapping them in additional html """
    html = '<table id="survey-questions">'
    for i, question in enumerate(self.questions):
      html += '<tr><th>{}.</th><td>{}{}</td></tr>'.format(
          i + 1, question['question'], rendered_widgets[i])
    html += '</table>'
    return html

  def value_from_datadict(self, data, files, name):
    """ Consolidate widget data into a single value for storage
      Returns json encoded string for questions field """

    val_list = []
    for i, widget in enumerate(self.widgets):
      val_list.append(self.questions[i]['question'])
      val_list.append(widget.value_from_datadict(data, files, name + '_%s' % i))
    return json.dumps(val_list)


class SurveyResponseForm(ModelForm):

  class Meta:
    model = SurveyResponse
    fields = ['gp_survey', 'responses']
    widgets = {'date': widgets.HiddenInput(), 'gp_survey': widgets.HiddenInput()}

  def __init__(self, survey, *args, **kwargs):
    super(SurveyResponseForm, self).__init__(*args, **kwargs)
    self.fields['responses'].widget = DisplayQuestionsWidget(survey)

  def clean_responses(self):
    data = json.loads(self.cleaned_data['responses'])
    for response in data:
      if response is None or response == '':
        raise ValidationError('Please answer every question.')
    return self.cleaned_data['responses']


class GivingProjectAdminForm(ModelForm):
  fund_goal = IntegerCommaField(label='Fundraising goal', initial=0,
      help_text=('Fundraising goal agreed upon by the group. If 0, it will not be '
                 'displayed to members and they won\'t see a group progress chart '
                 'for money raised.'))

  class Meta:
    model = GivingProject
    exclude = []
