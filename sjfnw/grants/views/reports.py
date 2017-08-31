import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from sjfnw.grants.decorators import registered_org

logger = logging.getLogger('sjfnw')

def autosave_yer(request, award_id):
  """ Autosave a YERDraft """

  if not request.user.is_authenticated():
    return HttpResponse(LOGIN_URL, status=401)

  draft = get_object_or_404(models.YERDraft, award_id=award_id)

  if request.method == 'POST':
    draft.contents = json.dumps(request.POST)
    logger.info(draft.contents)
    draft.modified = timezone.now()
    draft.save()
    return HttpResponse('success')

@login_required(login_url=LOGIN_URL)
@registered_org()
def year_end_report(request, organization, award_id):

  # get award, make sure org matches
  award = get_object_or_404(models.GivingProjectGrant, pk=award_id)
  app = award.projectapp.application

  if app.organization_id != organization.pk:
    logger.warning('Trying to edit someone else\'s YER')
    return redirect(org_home)

  total_yers = models.YearEndReport.objects.filter(award=award).count()
  # check if already submitted
  if total_yers >= award.grant_length():
    logger.warning('Required YER(s) already submitted for this award')
    return redirect(org_home)

  # get or create draft
  draft, created = models.YERDraft.objects.get_or_create(award=award)
  if request.method == 'POST':
    draft_data = json.loads(draft.contents)
    files_data = model_to_dict(draft, fields=['photo1', 'photo2', 'photo3',
                                              'photo4', 'photo_release'])
    draft_data['award'] = award.pk
    form = YearEndReportForm(draft_data, files_data)
    if form.is_valid():
      yer = form.save()
      draft.delete()

      utils.send_email(
        subject='Year end report submitted',
        template='grants/email_yer_submitted.html',
        sender=c.GRANT_EMAIL,
        to=[yer.email]
      )
      logger.info('YER submission confirmation email sent to %s', yer.email)
      return redirect('/report/submitted')

    else:
      logger.info('Invalid YER:')
      logger.info(form.errors.items())

  else: # GET
    if created:
      initial_data = {'website': app.website, 'sit_website': app.website,
                      'contact_person': app.contact_person + ', ' + app.contact_person_title,
                      'phone': app.telephone_number, 'email': app.email_address}
      logger.info('Created new YER draft')
    else:
      initial_data = json.loads(draft.contents)
      # manually convert multi-widget TODO improve this
      initial_data['contact_person'] = (initial_data.get('contact_person_0', '') +
          ', ' + initial_data.get('contact_person_1', ''))

    form = YearEndReportForm(initial=initial_data)

  file_urls = get_file_urls(request, draft)
  for field, url in file_urls.iteritems():
    if url:
      name = getattr(draft, field).name.split('/')[-1]
      file_urls[field] = ('<a href="' + url + '" target="_blank" title="' +
          name + '">' + name + '</a> [<a onclick="fileUploads.removeFile(\'' +
          field + '\');">remove</a>]')
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  due = award.first_yer_due.replace(year=award.first_yer_due.year + total_yers)
  yer_period = '{:%b %d, %Y} - {:%b %d, %Y}'.format(due.replace(year=due.year - 1), due)

  return render(request, 'grants/yer_form.html', {
    'form': form,
    'org': organization,
    'draft': draft,
    'award': award,
    'file_urls': file_urls,
    'user_override': get_user_override(request),
    'yer_period': yer_period
  })

