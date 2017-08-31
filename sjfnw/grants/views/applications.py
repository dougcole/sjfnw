
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


@login_required_ajax(login_url=LOGIN_URL)
@registered_org()
def autosave_app(request, organization, cycle_id):
  """ Save non-file fields to a draft """

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  draft = get_object_or_404(models.DraftGrantApplication,
      organization=organization, grant_cycle=cycle)

  if request.method == 'POST':
    curr_user = request.POST.get('user_id')

    # check for simultaneous editing
    if request.GET.get('force') != 'true':
      if draft.recently_edited():
        if draft.modified_by and draft.modified_by != curr_user:
          # last save wasn't this userid
          logger.info('Requiring confirmation')
          return HttpResponse('confirm force', status=409)
    else:
      logger.info('Force - skipped check')

    logger.debug('Autosaving')
    draft.contents = json.dumps(request.POST)
    draft.modified = timezone.now()
    draft.modified_by = curr_user or 'none'
    draft.save()
    return HttpResponse('success')

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

      for cn in models.CycleNarrative.objects.filter(grant_cycle=cycle).select_related('narrative_question'):
        text = form.cleaned_data.get(cn.narrative_question.name)
        answer = models.NarrativeAnswer(cycle_narrative=cn, grant_application=application, text=text)
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
    draft = models.DraftGrantApplication.objects.filter(**filter_by).first()

    if draft is None:
      if not cycle.is_open():
        return render(request, 'grants/closed.html', {'cycle': cycle})
      if cycle.info_page and not request.GET.get('info'):
        return redirect(reverse(cycle_info, kwargs={'cycle_id': cycle.pk}))

      draft = models.DraftGrantApplication(**filter_by)
      profiled = _autofill_draft(draft)
      if not profiled: # wasn't saved by _autofill_draft
        draft.save()

    else:
      if not draft.editable():
        return render(request, 'grants/closed.html', {'cycle': cycle})
      if draft.contents == '{}': # if draft was created via admin site
        profiled = _autofill_draft(draft)

    draft_contents = json.loads(draft.contents)
    format_draft_contents(draft_contents)
    form = get_form_for_cycle(cycle)(cycle, initial=draft_contents)

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


