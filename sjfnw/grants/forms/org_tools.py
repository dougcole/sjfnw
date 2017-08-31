import logging

from django import forms

from sjfnw.grants.models import (Organization, GrantCycle, GrantApplication,
    DraftGrantApplication)

logger = logging.getLogger('sjfnw')


class RolloverForm(forms.Form):
  """ Used by organizations to copy a draft or app into another grant cycle

  Fields (created on init):
    application - any of org's submitted apps
    draft - any of org's drafts
    cycle - any open cycle that does not have a submission or draft
  """

  def __init__(self, organization, *args, **kwargs):
    super(RolloverForm, self).__init__(*args, **kwargs)

    submitted = (GrantApplication.objects.select_related('grant_cycle')
                                         .filter(organization=organization)
                                         .order_by('-submission_time'))
    drafts = (DraftGrantApplication.objects.select_related('grant_cycle')
                                           .filter(organization=organization))

    # filter out cycles covered by apps/drafts, get remaining open ones
    exclude_cycles = ([draft.grant_cycle.pk for draft in drafts] +
                      [sub.grant_cycle.pk for sub in submitted])
    cycles = (GrantCycle.objects.filter(open__lt=timezone.now(), close__gt=timezone.now())
                                .exclude(id__in=exclude_cycles))

    # create fields
    self.fields['application'] = forms.ChoiceField(
        required=False, initial=0,
        choices=[('', '--- Submitted applications ---')] +
                [(a.id, u'{} - submitted {:%m/%d/%y}'.format(a.grant_cycle, a.submission_time))
                 for a in submitted])
    self.fields['draft'] = forms.ChoiceField(
        required=False, initial=0,
        choices=[('', '--- Saved drafts ---')] +
                [(d.id, u'{} - modified {:%m/%d/%y}'.format(d.grant_cycle, d.modified))
                 for d in drafts])
    self.fields['cycle'] = forms.ChoiceField(
        choices=[('', '--- Open cycles ---')] + [(c.id, unicode(c)) for c in cycles])

  def clean(self):
    cleaned_data = super(RolloverForm, self).clean()
    cycle = cleaned_data.get('cycle')
    application = cleaned_data.get('application')
    draft = cleaned_data.get('draft')

    if not cycle:
      self._errors['cycle'] = self.error_class(['Required.'])
    else:
      try:
        cycle_obj = GrantCycle.objects.get(pk=int(cycle))
      except GrantCycle.DoesNotExist:
        logger.error('RolloverForm submitted cycle does not exist')
        self._errors['cycle'] = self.error_class(
            ['Grant cycle could not be found. Please refresh the page and try again.'])

      if not cycle_obj.is_open:
        self._errors['cycle'] = self.error_class(
            ['That cycle has closed.  Select a different one.'])

    if not draft and not application:
      self._errors['draft'] = self.error_class(['Select one.'])
    elif draft and application:
      self._errors['draft'] = self.error_class(['Select only one.'])

    return cleaned_data

class RolloverYERForm(forms.Form):
  """ Used to copy a year-end report for use with another gp grant
  Fields (created on init):
    report - submitted YearEndReport
    award - GPGrant to copy it to
  """

  def __init__(self, reports, awards, *args, **kwargs):
    super(RolloverYERForm, self).__init__(*args, **kwargs)
    self.fields['report'] = forms.ChoiceField(
        choices=[('', '--- Year-end reports ---')] +
                [(r.id, unicode(r) + ' ({:%-m/%-d/%y})'.format(r.submitted)) for r in reports])
    self.fields['award'] = forms.ChoiceField(
        label='Grant', choices=[('', '--- Grants ---')] + [(a.id, unicode(a)) for a in awards])
