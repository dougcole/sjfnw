import json
import logging

from django import forms
from django.forms import ValidationError, ModelForm
from django.db.models import PositiveIntegerField
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

from sjfnw.forms import IntegerCommaField, PhoneNumberField
from sjfnw.grants import constants as gc
from sjfnw.grants.models import (Organization, GrantApplication, DraftGrantApplication,
    YearEndReport, CycleNarrative)

logger = logging.getLogger('sjfnw')


def _form_error(text):
  return '<div class="form_error">%s</div>' % text


class OrgProfile(ModelForm):

  class Meta:
    model = Organization
    fields = Organization.get_profile_fields()

class CycleNarrativeFormset(forms.models.BaseInlineFormSet):

  class Meta:
    model = CycleNarrative

  def clean(self):
    orders = [form.cleaned_data['order'] for form in self.forms]
    if len(set(orders)) < len(orders):
      raise forms.ValidationError('Cannot have multiple questions with the same order')


class TimelineWidget(forms.widgets.MultiWidget):

  def __init__(self, attrs=None, quarters=5):
    self._quarters = quarters
    _widgets = []
    for _ in range(0, quarters):
      _widgets.append(forms.Textarea(attrs={'rows': '5', 'cols': '20'}))
      _widgets.append(forms.Textarea(attrs={'rows': '5'}))
      _widgets.append(forms.Textarea(attrs={'rows': '5'}))
    super(TimelineWidget, self).__init__(_widgets, attrs)

  def decompress(self, value):
    """ break single database value up for widget display
          argument: database value (json string representing list of vals)
          returns: list of values to be displayed in widgets """

    if value:
      return json.loads(value)
    return [None for _ in range(0, self._quarters * 3)]

  def format_output(self, rendered_widgets):
    """
    format the widgets for display
      args: list of rendered widgets
      returns: a string of HTML for displaying the widgets
    """

    html = ('<table id="timeline_form"><tr class="heading"><td></td>'
            '<th>Date range</th><th>Activities<br><i>(What will you be doing?)</i></th>'
            '<th>Goals/objectives<br><i>(What do you hope to achieve?)</i></th></tr>')
    for i in range(0, len(rendered_widgets), 3):
      html += ('<tr><th class="left">Quarter ' + str(i / 3 + 1) + '</th><td>' +
              rendered_widgets[i] + '</td><td>' + rendered_widgets[i + 1] +
              '</td><td>' + rendered_widgets[i + 2] + '</td></tr>')
    html += '</table>'
    return html

  def value_from_datadict(self, data, files, name):
    """ Consolodate widget data into a single value
        returns:
          json'd list of values """

    val_list = []
    for i, widget in enumerate(self.widgets):
      val_list.append(widget.value_from_datadict(data, files, '{}_{}'.format(name, i)))
    return json.dumps(val_list)


def custom_fields(field, **kwargs): # sets phonenumber and money fields
  money_fields = ['budget_last', 'budget_current', 'amount_requested', 'project_budget']
  # disabling this under PhoneNumberField can handle extensions
  # phone_fields = ['telephone_number', 'fax_number', 'fiscal_telephone',
  #                 'collab_ref1_phone', 'collab_ref2_phone',
  #                'racial_justice_ref1_phone', 'racial_justice_ref2_phone']
  kwargs['required'] = not field.blank
  if field.verbose_name:
    kwargs['label'] = capfirst(field.verbose_name)
  if field.name in money_fields:
    return IntegerCommaField(**kwargs)
  # elif field.name in phone_fields:
  #   return PhoneNumberField(**kwargs)
  else:
    return field.formfield(**kwargs)

class GrantApplicationModelForm(forms.ModelForm):

  two_year_question = forms.CharField(required=False,
      widget=forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['two_year_question']
      }))

  formfield_callback = custom_fields

  class Meta:
    model = GrantApplication
    exclude = ['pre_screening_status', 'submission_time', 'giving_projects']
    widgets = {
      'mission': forms.Textarea(attrs={
        'rows': 3,
        'class': 'wordlimited',
        'data-limit': 150
      }),
      'grant_request': forms.Textarea(attrs={
        'rows': 3,
        'class': 'wordlimited',
        'data-limit': 100
      }),
      'support_type': forms.RadioSelect(),
      'narrative1': forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['narrative1']
      }),
      'narrative2': forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['narrative2']
      }),
      'narrative3': forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['narrative3']
      }),
      'narrative4': forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['narrative4']
      }),
      'narrative5': forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['narrative5']
      }),
      'narrative6': forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['narrative6']
      }),
      'cycle_question': forms.Textarea(attrs={
        'class': 'wordlimited',
        'data-limit': gc.NARRATIVE_WORD_LIMITS['cycle_question']
      }),
      'timeline': TimelineWidget()
    }

  def __init__(self, cycle, *args, **kwargs):
    super(GrantApplicationModelForm, self).__init__(*args, **kwargs)
    if cycle:
      if cycle.extra_question:
        self.fields['cycle_question'].required = True
        self.fields['cycle_question'].label = cycle.extra_question
        logger.info('Requiring the cycle question')
      if cycle.two_year_grants:
        self.fields['two_year_question'].required = True
        self.fields['two_year_question'].label = cycle.two_year_question
        logger.info('Requiring the two-year question')

    # hack to support customized grant cycles. pk matches prod, name is for local dev
    if cycle.pk == 35 or cycle.title == "Displaced Tenants Fund":
      logger.info('Setting customized questions texts for Displaced Tenants Fund')
      for i in range(1, 7):
        field_name = 'narrative{}'.format(i)
        self.fields[field_name].label = gc.NARRATIVE_TEXTS_DT[field_name]
    elif cycle.pk == 36 or cycle.title == "EPIC Zero Detention Project":
      logger.info('Setting customized questions texts for EPIC Zero Detention Project')
      self.fields['timeline'].widget = TimelineWidget(quarters=4)
      self.fields['timeline'].label = gc.NARRATIVE_TEXTS_EPIC['timeline']
      for i in range(1, 7):
        field_name = 'narrative{}'.format(i)
        self.fields[field_name].label = gc.NARRATIVE_TEXTS_EPIC[field_name]

  def clean(self):
    cleaned_data = super(GrantApplicationModelForm, self).clean()

    # timeline
    timeline = json.loads(cleaned_data.get('timeline'))
    empty = False
    incomplete = False
    for i in range(2, len(timeline), 3):
      date = timeline[i - 2]
      act = timeline[i - 1]
      obj = timeline[i]

      if i == 2 and not (date or act or obj):
        empty = True
      if (date or act or obj) and not (date and act and obj):
        incomplete = True

    if incomplete:
      self._errors['timeline'] = _form_error('All three columns are required '
          'for each quarter that you include in your timeline.')
    elif empty:
      self._errors['timeline'] = _form_error('This field is required.')

    # collab refs - require phone or email
    phone = cleaned_data.get('collab_ref1_phone')
    email = cleaned_data.get('collab_ref1_email')
    if not phone and not email:
      self._errors['collab_ref1_phone'] = _form_error('Enter a phone number or email.')
    phone = cleaned_data.get('collab_ref2_phone')
    email = cleaned_data.get('collab_ref2_email')
    if not phone and not email:
      self._errors['collab_ref2_phone'] = _form_error('Enter a phone number or email.')

    # racial justice refs - require full set if any
    name = cleaned_data.get('racial_justice_ref1_name')
    org = cleaned_data.get('racial_justice_ref1_org')
    phone = cleaned_data.get('racial_justice_ref1_phone')
    email = cleaned_data.get('racial_justice_ref1_email')
    if name or org or phone or email:
      if not name:
        self._errors['racial_justice_ref1_name'] = _form_error('Enter a contact person.')
      if not org:
        self._errors['racial_justice_ref1_org'] = _form_error('Enter the organization name.')
      if not phone and not email:
        self._errors['racial_justice_ref1_phone'] = _form_error('Enter a phone number or email.')
    name = cleaned_data.get('racial_justice_ref2_name')
    org = cleaned_data.get('racial_justice_ref2_org')
    phone = cleaned_data.get('racial_justice_ref2_phone')
    email = cleaned_data.get('racial_justice_ref2_email')
    if name or org or phone or email:
      if not name:
        self._errors['racial_justice_ref2_name'] = _form_error('Enter a contact person.')
      if not org:
        self._errors['racial_justice_ref2_org'] = _form_error('Enter the organization name.')
      if not phone and not email:
        self._errors['racial_justice_ref2_phone'] = _form_error('Enter a phone number or email.')

    # project - require title & budget if type
    support_type = cleaned_data.get('support_type')
    if support_type == 'Project support':
      if not cleaned_data.get('project_budget'):
        self._errors['project_budget'] = _form_error(
            'This field is required when applying for project support.')
      if not cleaned_data.get('project_title'):
        self._errors['project_title'] = _form_error(
            'This field is required when applying for project support.')

    # fiscal info/file - require all if any
    org = cleaned_data.get('fiscal_org')
    person = cleaned_data.get('fiscal_person')
    phone = cleaned_data.get('fiscal_telephone')
    email = cleaned_data.get('fiscal_email')
    address = cleaned_data.get('fiscal_address')
    city = cleaned_data.get('fiscal_city')
    state = cleaned_data.get('fiscal_state')
    zipcode = cleaned_data.get('fiscal_zip')
    fiscal_letter = cleaned_data.get('fiscal_letter')
    if org or person or phone or email or address or city or state or zipcode:
      if not org:
        self._errors['fiscal_org'] = _form_error('This field is required.')
      if not person:
        self._errors['fiscal_person'] = _form_error('This field is required.')
      if not phone:
        self._errors['fiscal_telephone'] = _form_error('This field is required.')
      if not email:
        self._errors['fiscal_email'] = _form_error('This field is required.')
      if not address:
        self._errors['fiscal_address'] = _form_error('This field is required.')
      if not city:
        self._errors['fiscal_city'] = _form_error('This field is required.')
      if not state:
        self._errors['fiscal_state'] = _form_error('This field is required.')
      if not zipcode:
        self._errors['fiscal_zip'] = _form_error('This field is required.')
      if not fiscal_letter:
        self._errors['fiscal_letter'] = _form_error('This field is required.')

    return cleaned_data


class ContactPersonWidget(forms.widgets.MultiWidget):
  """ Displays widgets for contact person and their title
  Stores in DB as a single value: Name, title """

  def __init__(self, attrs=None):
    _widgets = (forms.TextInput(), forms.TextInput())
    super(ContactPersonWidget, self).__init__(_widgets, attrs)

  def decompress(self, value):
    """ break single db value up for display
    returns list of values to be displayed in widgets """
    if value:
      return [val for val in value.split(', ', 1)]
    else:
      return [None, None]

  def format_output(self, rendered_widgets):
    """ format widgets for display - add any additional labels, html, etc """
    return (rendered_widgets[0] +
            '<label for="contact_person_1" style="margin-left:5px">Title</label>' +
            rendered_widgets[1])

  def value_from_datadict(self, data, files, name):
    """ Consolidate widget data into single value for db storage """

    val_list = []
    for i, widget in enumerate(self.widgets):
      val_list.append(widget.value_from_datadict(data, files, name + '_%s' % i))
    val = ', '.join(val_list)
    if val == ', ':
      return ''
    else:
      return val


def set_yer_custom_fields(field, **kwargs):
  kwargs['required'] = not field.blank
  if field.verbose_name:
    kwargs['label'] = capfirst(field.verbose_name)
  if field.name == 'phone':
    return PhoneNumberField(**kwargs)
  elif isinstance(field, PositiveIntegerField):
    return IntegerCommaField(**kwargs)
  else:
    return field.formfield(**kwargs)


class YearEndReportForm(ModelForm):
  # add individual stay in touch components
  listserve = forms.CharField(required=False)
  sit_website = forms.CharField(required=False, label='Website')
  newsletter = forms.CharField(required=False)
  facebook = forms.CharField(required=False)
  twitter = forms.CharField(required=False)
  other = forms.CharField(required=False)

  formfield_callback = set_yer_custom_fields

  class Meta:
    model = YearEndReport
    exclude = ['submitted', 'visible']
    widgets = {'award': forms.HiddenInput(),
               'stay_informed': forms.HiddenInput(),
               'contact_person': ContactPersonWidget}

  def clean(self):
    stay_informed = {}
    # declared_fields = the fields listed above (rather than fields inferred from model)
    for field_name in self.declared_fields:
      val = self.cleaned_data.get(field_name, None)
      if val:
        stay_informed[field_name] = val
    if stay_informed:
      self.cleaned_data['stay_informed'] = json.dumps(stay_informed)
    else:
      self._errors['stay_informed'] = mark_safe(
        '<ul class="errorlist"><li>Please fill out at least one of the options below.</li></ul>'
      )
    return super(YearEndReportForm, self).clean()

# ADMIN

class DraftAdminForm(ModelForm):
  class Meta:
    model = DraftGrantApplication
    exclude = []

  def clean(self):
    cleaned_data = super(DraftAdminForm, self).clean()
    org = cleaned_data.get('organization')
    cycle = cleaned_data.get('grant_cycle')
    if org and cycle:
      if GrantApplication.objects.filter(organization=org, grant_cycle=cycle):
        raise ValidationError('This organization has already submitted an '
                              'application to this grant cycle.')
    return cleaned_data

class LogAdminForm(ModelForm):

  def __init__(self, *args, **kwargs):
    super(LogAdminForm, self).__init__(*args, **kwargs)
    if self.instance and self.instance.organization_id:
      self.fields['application'].queryset = GrantApplication.objects.filter(
          organization_id=self.instance.organization_id)
