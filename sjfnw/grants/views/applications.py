import json, logging

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.shortcuts import render, get_object_or_404, redirect

from sjfnw import constants as c, utils
from sjfnw.grants import models
from sjfnw.grants.decorators import registered_org
from sjfnw.grants.modelforms import get_form_for_cycle
from sjfnw.grants.views.cycles import cycle_info
from sjfnw.grants.views.helpers import get_file_urls, get_viewing_permission
from sjfnw.grants.utils import get_user_override

logger = logging.getLogger('sjfnw')

LOGIN_URL = '/apply/login/'

def _load_draft(draft):
  org_dict = json.loads(draft.contents)
  timeline = []
  for i in range(15): # covering both timeline formats
    if 'timeline_' + str(i) in org_dict:
      timeline.append(org_dict['timeline_' + str(i)])
  org_dict['timeline'] = json.dumps(timeline)
  return org_dict

def _autofill_draft(draft):
  """ If org has profile information, use it to autofill draft fields
    Returns: indicator of whether draft was updated. """
  if draft.organization.mission:
    org_dict = model_to_dict(draft.organization, exclude=['fiscal_letter'])
    draft.fiscal_letter = draft.organization.fiscal_letter
    draft.contents = json.dumps(org_dict)
    draft.save()
    logger.debug('Autofilled draft %s, %s', draft.organization, draft.grant_cycle)
    return True
  return False


@login_required(login_url=LOGIN_URL)
@registered_org()
def grant_application(request, organization, cycle_id):
  """ Get or submit the whole application form
    The first time an org visits this page, it will redirect to cycle info page.
  """

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)

  filter_by = {'organization': organization, 'grant_cycle': cycle}

  # check for app already submitted
  if models.GrantApplication.objects.filter(**filter_by).exists():
    return render(request, 'grants/already_applied.html', {
      'organization': organization, 'cycle': cycle
    })

  profiled = False

  if request.method == 'POST':
    draft = get_object_or_404(models.DraftGrantApplication, **filter_by)
    if not draft.editable():
      return render(request, 'grants/submitted_closed.html', {'cycle': cycle})

    # application data is not sent in POST request
    # all the grant application data is saved on the DraftGrantApplication
    # and POST request just indicates that they wish to submit it

    # get fields & files from draft
    draft_data = json.loads(draft.contents)
    files_data = model_to_dict(draft, fields=draft.file_fields())

    # add automated fields
    draft_data['organization'] = organization.pk
    draft_data['grant_cycle'] = cycle.pk

    form = get_form_for_cycle(cycle)(cycle, draft_data, files_data)

    if form.is_valid():
      logger.info('Application form valid')

      application = form.save()

      cycle_narratives = (models.CycleNarrative.objects
          .filter(grant_cycle=cycle)
          .select_related('narrative_question'))

      for c_narrative in cycle_narratives:
        text = form.cleaned_data.get(c_narrative.narrative_question.name)
        answer = models.NarrativeAnswer(
          cycle_narrative=c_narrative, grant_application=application, text=text
        )
        answer.save()

      to_email = organization.get_email()
      utils.send_email(
        subject='Grant application submitted',
        sender=c.GRANT_EMAIL,
        to=[to_email],
        template='grants/email_submitted.html',
        context={'org': organization, 'cycle': cycle}
      )
      logger.info('Application submitted for %s; confirmation email sent to %s',
        organization.name, to_email)

      draft.delete()

      return redirect('/apply/submitted')

    else: # INVALID SUBMISSION
      logger.info('Application form invalid. Errors for fields: %s',
          ', '.join(form.errors.keys()))

  else: # GET
    if not cycle.is_open():
      return render(request, 'grants/closed.html', {'cycle': cycle})

    draft = models.DraftGrantApplication.objects.filter(**filter_by).first()

    # if they weren't sent here from info page and draft has not been created, redirect
    if cycle.info_page and not request.GET.get('info') and draft is None:
      return redirect(reverse(cycle_info, kwargs={'cycle_id': cycle.pk}))

    if draft is None:
      draft = models.DraftGrantApplication(**filter_by)
      profiled = _autofill_draft(draft)
      if not profiled: # wasn't saved by _autofill_draft
        draft.save()
    elif draft.contents == '{}': # if draft was created via admin site
      profiled = _autofill_draft(draft)

    org_dict = _load_draft(draft)
    form = get_form_for_cycle(cycle)(cycle, initial=org_dict)

  # get draft files
  file_urls = get_file_urls(request, draft)
  link_template = (u'<a href="{0}" target="_blank" title="{1}">{1}</a> '
                   '[<a onclick="fileUploads.removeFile(\'{2}\');">remove</a>]')
  for field, url in file_urls.iteritems():
    if url:
      name = getattr(draft, field).name.split('/')[-1]
      file_urls[field] = link_template.format(url, name, field)
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  return render(request, 'grants/org_app.html', {
    'form': form,
    'cycle': cycle,
    'file_urls': file_urls,
    'draft': draft,
    'profiled': profiled,
    'org': organization,
    'user_override': get_user_override(request),
    'flag': draft.recently_edited() and draft.modified_by
  })

def view_application(request, app_id):
  app = get_object_or_404(models.GrantApplication, pk=app_id)
  answers = (models.NarrativeAnswer.objects
      .filter(grant_application=app)
      .select_related('cycle_narrative__narrative_question')
      .order_by('cycle_narrative__order'))

  if not request.user.is_authenticated():
    perm = 0
  else:
    perm = get_viewing_permission(request.user, app)
  logger.info('perm is ' + str(perm))

  form = get_form_for_cycle(app.grant_cycle)(app.grant_cycle)

  form_only = request.GET.get('form')
  if form_only:
    return render(request, 'grants/reading.html',
                  {'app': app, 'form': form, 'perm': perm})
  file_urls = get_file_urls(request, app)
  print_urls = get_file_urls(request, app, printing=True)
  awards = {}
  for papp in app.projectapp_set.all():
    if hasattr(papp, 'givingprojectgrant'):# and hasattr(papp.givingprojectgrant, 'yearendreport'):
      awards[papp.giving_project] = papp.givingprojectgrant

  return render(request, 'grants/reading_sidebar.html', {
    'app': app, 'answers': answers, 'form': form, 'file_urls': file_urls,
    'print_urls': print_urls, 'awards': awards, 'perm': perm
  })
