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
  """ Match the format used by django """
  return '<ul class="errorlist"><li>%s</li></ul>' % text


class OrgProfile(ModelForm):

  class Meta:
    model = Organization
    fields = Organization.get_profile_fields()


class CycleNarrativeFormset(forms.models.BaseInlineFormSet):

  class Meta:
    model = CycleNarrative

  def clean(self):
    super(CycleNarrativeFormset, self).clean()
    orders = []
    for form in self.forms:
      data = form.cleaned_data
      if data.get('order') and data.get('narrative_question'):
        orders.append(data.get('order'))
      else:
        return
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

  formfield_callback = custom_fields

  class Meta:
    model = GrantApplication
    exclude = ['narratives', 'pre_screening_status', 'submission_time', 'giving_projects']
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
      'support_type': forms.RadioSelect()
    }

  def __init__(self, cycle, *args, **kwargs):
    super(GrantApplicationModelForm, self).__init__(*args, **kwargs)

    # TODO hacky
    if cycle.get_type() == 'standard':
      self.fields['status'] = forms.ChoiceField(choices = gc.STATUS_CHOICES[:-1])
    else:
      for field in GrantApplication.file_fields():
        self.fields[field].required = False
      if cycle.get_type() == 'rapid':
        self.fields['demographics'].required = True

    narratives = cycle.narrative_questions.order_by('cyclenarrative__order')
    self._narrative_fields = []

    for n in narratives:
      if n.name == 'timeline':
        widget = TimelineWidget()
      elif '_references' in n.name:
        widget = ReferencesMultiWidget()
      else:
        widget = forms.Textarea(attrs={
          'class': 'wordlimited',
          'data-limit': n.word_limit
        })
      field = forms.CharField(label=n.text, widget=widget)
      self.fields[n.name] = field
      self._narrative_fields.append(n.name)

  def clean_collaboration_references(self):
    collab_refs = json.loads(self.cleaned_data.get('collaboration_references'))
    msg = 'Please include a name, organization, and phone or email for each reference.'
    for ref in collab_refs:
      if not ref.get('name') or not ref.get('org'):
        raise ValidationError(msg)
      if not ref.get('phone') and not ref.get('email'):
        raise ValidationError(msg)

    return self.cleaned_data.get('collaboration_references')

  def clean_racial_justice_references(self):
    rj_refs = json.loads(self.cleaned_data.get('racial_justice_references'))
    msg = 'Please include a name, organization, and phone or email for each reference you include.'
    for i in [0, 1]:
      if len(rj_refs) <= i:
        return
      ref = rj_refs[i]
      name = ref.get('name')
      org = ref.get('org')
      phone = ref.get('phone')
      email = ref.get('email')
      has_any = name or org or phone or email
      if has_any and (not name or not org or (not phone and not email)):
        raise ValidationError(msg)

  def clean_timeline(self):
    timeline = json.loads(self.cleaned_data.get('timeline'))

    for i in range(2, len(timeline), 3):
      date = timeline[i - 2]
      action = timeline[i - 1]
      objective = timeline[i]

      if i == 2 and not (date or action or objective):
        raise ValidationError('This field is required.')
      if (date or action or objective) and not (date and action and objective):
        raise ValidationError('All three columns are required for each quarter that you include in your timeline.')

    return self.cleaned_data.get('timeline')

  def clean(self):
    cleaned_data = super(GrantApplicationModelForm, self).clean()

    # project - require title & budget if type
    support_type = cleaned_data.get('support_type')
    if support_type == 'Project support':
      if not cleaned_data.get('project_budget'):
        self._errors['project_budget'] = _form_error(
            'This field is required when applying for project support.')
      if not cleaned_data.get('project_title'):
        self._errors['project_title'] = _form_error(
            'This field is required when applying for project support.')

    self._validate_fiscal_info(cleaned_data)

    return cleaned_data

  def _validate_fiscal_info(self, cleaned_data):
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

  def get_narrative_fields(self):
    return [self[n] for n in self._narrative_fields]


class ReferencesMultiWidget(forms.widgets.MultiWidget):
  """ Displays fields for entering 2 references (collab/racial justice)
   Stored in DB as single JSON string """

  def __init__(self, attrs=None):
    _widgets = [
        forms.TextInput(),
        forms.TextInput(),
        forms.TextInput(),
        forms.EmailInput(),
        forms.TextInput(),
        forms.TextInput(),
        forms.TextInput(),
        forms.EmailInput()
    ]
    super(ReferencesMultiWidget, self).__init__(_widgets, attrs)

  def decompress(self, value):
    """ break single database value up for widget display
        argument: database value (json string)
        returns: list of values to be displayed in widgets """

    if value:
      refs = json.loads(value)
      vals = []
      for ref in refs:
        vals += [ref['name'], ref['org'], ref['phone'], ref['email']]
      return vals
    return [None for _ in range(0, 8)]

  def format_output(self, rendered_widgets):
    """
    format the widgets for display
      args: list of rendered widgets
      returns: a string of HTML for displaying the widgets
    """

    wrapper = '<div class="col col-1of4">{}</div>'
    row_start = '<div class="row">'
    row_end = '</div>'
    html = (row_start + wrapper.format('Name') + wrapper.format('Organization') +
        wrapper.format('Phone') + wrapper.format('Email') + row_end)
    wrapped = [wrapper.format(w) for w in rendered_widgets]
    for i in [0, 1]:
      html += row_start
      for j in range(0, 4):
        html += wrapper.format(rendered_widgets[j + i * 4])
      html += row_end

    return html

  def value_from_datadict(self, data, files, name):
    """ Consolodate widget data into a single value
        returns:
          json'd list of values """

    values = []

    for i in range(0, 1):
      j = i * 4
      values.append({
        'name': data.get('{}_{}'.format(name, j)),
        'org': data.get('{}_{}'.format(name, j + 1)),
        'phone': data.get('{}_{}'.format(name, j + 2)),
        'email': data.get('{}_{}'.format(name, j + 3)),
      })

    return json.dumps(values)


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
    widgets = {
      'award': forms.HiddenInput(),
      'stay_informed': forms.HiddenInput(),
      'total_size': forms.TextInput(attrs={'class': 'input-s'}),
      'donations_count_prev': forms.TextInput(attrs={'class': 'input-s'}),
      'donations_count': forms.TextInput(attrs={'class': 'input-s'}),
      'total_size': forms.TextInput(attrs={'class': 'input-s'}),
      'contact_person': ContactPersonWidget
    }

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
