import json
import logging

from django import forms
from django.forms import ValidationError, ModelForm
from django.db.models import PositiveIntegerField
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

from sjfnw.forms import IntegerCommaField, PhoneNumberField
from sjfnw.grants import constants as gc, utils
from sjfnw.grants.models import (Organization, GrantApplication, DraftGrantApplication,
    YearEndReport, NarrativeQuestion, CycleNarrative)

logger = logging.getLogger('sjfnw')


def _form_error(text):
  """ Match the format used by django """
  return '<ul class="errorlist"><li>%s</li></ul>' % text


class NarrativeQuestionForm(forms.ModelForm):

  archived = forms.BooleanField(
    required=False,
    help_text='Archived questions remain associated with existing grant cycles but can\'t be used in new grant cycles.'
  )

  class Meta:
    model = NarrativeQuestion
    fields = ('name', 'version', 'archived', 'text', 'word_limit')

  def __init__(self, *args, **kwargs):
    # convert date field to boolean display
    # instance may be missing or None
    if kwargs.get('instance', None) and kwargs['instance'].archived:
      kwargs['initial'] = {'archived': True}
    super(NarrativeQuestionForm, self).__init__(*args, **kwargs)


  def clean(self, *args, **kwargs):
    archive = self.cleaned_data.get('archived')
    was_archived = self.instance.archived

    # convert boolean input to date field
    if archive and not was_archived:
      self.cleaned_data['archived'] = unicode(timezone.now().date())
    elif not archive and was_archived:
      self.cleaned_data['archived'] = None
    else: # no change
      self.cleaned_data['archived'] = was_archived
    super(NarrativeQuestionForm, self).clean(*args, **kwargs)

    # disallow unarchived question with same name/version as another
    name = self.cleaned_data.get('name')
    version = self.cleaned_data.get('version')
    if name and version and not self.cleaned_data.get('archived'):
      conflict = NarrativeQuestion.objects.filter(
        name=self.cleaned_data.get('name'),
        version=self.cleaned_data.get('version'),
        archived__isnull=True
      )
      if self.instance.pk:
        conflict = conflict.exclude(pk=self.instance.pk)
      if conflict.exists():
        raise ValidationError('Cannot have two active questions with the same name and version. Use a different version or archive the other question')


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
  template_name = 'grants/widgets/timeline.html'

  def __init__(self, attrs=None, quarters=5):
    self._quarters = quarters
    _widgets = []
    for i in range(0, quarters):
      # total hack to make quarter accessible in template
      _widgets.append(forms.Textarea(attrs={'rows': '5', 'cols': '20', 'quarter': i + 1 }))
      _widgets.append(forms.Textarea(attrs={'rows': '5'}))
      _widgets.append(forms.Textarea(attrs={'rows': '5'}))

    print('init', [getattr(w, 'quarter', None) for w in _widgets])
    super(TimelineWidget, self).__init__(_widgets, attrs)

  def decompress(self, value):
    """ break single database value up for widget display
          argument: database value (json string representing list of vals)
          returns: list of values to be displayed in widgets """

    if value:
      return json.loads(value)
    return [None for _ in range(0, self._quarters * 3)]

  def value_from_datadict(self, data, files, name):
    """ Consolodate widget data into a single value
        returns:
          json'd list of values """

    val_list = []
    for i, widget in enumerate(self.widgets):
      val_list.append(widget.value_from_datadict(data, files, '{}_{}'.format(name, i)))
    return json.dumps(val_list)


def custom_fields(field, **kwargs): # sets money fields
  money_fields = ['budget_last', 'budget_current', 'amount_requested', 'project_budget']
  kwargs['required'] = not field.blank
  if field.verbose_name:
    kwargs['label'] = capfirst(field.verbose_name)
  if field.name in money_fields:
    return IntegerCommaField(**kwargs)
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

    if cycle.amount_note:
      self.fields['amount_requested'].label += ' ({})'.format(cycle.amount_note)

    narratives = cycle.narrative_questions.order_by('cyclenarrative__order')
    self._narrative_fields = []

    for n in narratives:
      if n.name == 'timeline':
        widget = TimelineWidget()
      elif '_references' in n.name:
        widget = ReferencesMultiWidget()
      elif n.word_limit:
        widget = forms.Textarea(attrs={
          'class': 'wordlimited',
          'data-limit': n.word_limit
        })
      else:
        widget = forms.Textarea()
      field = forms.CharField(label=n.text, widget=widget, required=True)
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
    for ref in rj_refs:
      name = ref.get('name')
      org = ref.get('org')
      phone = ref.get('phone')
      email = ref.get('email')
      has_any = name or org or phone or email
      if has_any and not (name and org and (phone or email)):
        raise ValidationError(msg)

    return self.cleaned_data.get('racial_justice_references')

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
    super(GrantApplicationModelForm, self).clean()

    # project - require title & budget if type
    if self.cleaned_data.get('support_type', '') == 'Project support':
      if not self.cleaned_data.get('project_budget'):
        self._errors['project_budget'] = _form_error(
            'This field is required when applying for project support.')
      if not self.cleaned_data.get('project_title'):
        self._errors['project_title'] = _form_error(
            'This field is required when applying for project support.')

    self._validate_fiscal_info()

  def _validate_fiscal_info(self):
    # fiscal info/file - require all if any
    org = self.cleaned_data.get('fiscal_org')
    person = self.cleaned_data.get('fiscal_person')
    phone = self.cleaned_data.get('fiscal_telephone')
    email = self.cleaned_data.get('fiscal_email')
    address = self.cleaned_data.get('fiscal_address')
    city = self.cleaned_data.get('fiscal_city')
    state = self.cleaned_data.get('fiscal_state')
    zipcode = self.cleaned_data.get('fiscal_zip')
    fiscal_letter = self.cleaned_data.get('fiscal_letter')
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


class SeedApplicationForm(GrantApplicationModelForm):

  class Meta(GrantApplicationModelForm.Meta):
    exclude = GrantApplicationModelForm.Meta.exclude + [
      'support_type', 'budget1', 'budget2', 'budget3',
      'funding_sources', 'project_title', 'project_budget',
      'project_budget_file'
    ]

class RapidResponseApplicationForm(GrantApplicationModelForm):

  class Meta(GrantApplicationModelForm.Meta):
    exclude = GrantApplicationModelForm.Meta.exclude + [
      'budget1', 'budget2', 'budget3', 'funding_sources',
      'project_budget_file'
    ]
    widgets = {
      'support_type': forms.HiddenInput()
    }

  def __init__(self, *args, **kwargs):
    kwargs.setdefault('initial', {})
    kwargs['initial'].setdefault('support_type', 'Project support')
    super(RapidResponseApplicationForm, self).__init__(*args, **kwargs)
    self.fields['support_type'].widget.attrs['readonly'] = True

class StandardApplicationForm(GrantApplicationModelForm):

  def __init__(self, *args, **kwargs):
    super(StandardApplicationForm, self).__init__(*args, **kwargs)
    self.fields['status'].choices = self.fields['status'].choices[:-1]
    for field in ['support_type', 'budget1', 'budget2', 'budget3', 'demographics', 'funding_sources']:
      self.fields[field].required = True
    kwargs.setdefault('initial', {})
    kwargs['initial'].setdefault('support_type', 'General support')

def get_form_for_cycle(cycle):
  cycle_type = cycle.get_type()
  if cycle_type == 'standard':
    return StandardApplicationForm
  elif cycle_type == 'rapid':
    return RapidResponseApplicationForm
  else:
    return SeedApplicationForm


class ReferencesMultiWidget(forms.widgets.MultiWidget):
  """ Displays fields for entering 2 references (collab/racial justice)
   Stored in DB as single JSON string """

  template_name = 'grants/widgets/references.html'

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
    """ Break single database value (json value) up for widget display
        argument: database value (json string)
        returns: list of values to be displayed in widgets """

    if value:
      vals = utils.flatten_references(json.loads(value))
    return [None for _ in range(0, 8)]

  def value_from_datadict(self, data, files, name):
    """ Consolodate widget data into a single value to store in db
      Returns: json string of field data
    """
    return json.dumps(utils.format_references(data, name))


class ContactPersonWidget(forms.widgets.MultiWidget):
  """ Displays widgets for contact person and their title
  Stores in DB as a single value: Name, title """

  template_name = 'grants/widgets/contact_person.html'

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
