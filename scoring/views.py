import logging
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from fund.decorators import approved_membership
from django.shortcuts import get_object_or_404, redirect
import grants.models
import models
import fund.models 
import grants.models

# Create your views here.


@login_required(login_url='/fund/login/')
@approved_membership()
def read_grant(request, app_id):
  membership = request.membership
  application = get_object_or_404(grants.models.GrantApplication, pk = app_id)
  form = grants.models.GrantApplicationForm()
  try:
    review = scoring.models.ApplicationRating.objects.get(application = application, membership = membership)
    logging.info('successfully retrieved form')
    scoring_form = models.RatingForm(instance=review)
  except:
    logging.info('creating a new form, app is ' + str(application))
    scoring_form = models.RatingForm(initial={'application': application, 'membership': membership})
    
    
  return render_to_response("scoring/reading.html", {'scoring_form': scoring_form, 'app':application, 'form':form})
  
#  "grant": models.GrantApplication.objects.get(pk=app_id)})
    

@login_required(login_url='/fund/login/')
def specific_project_admin(request, project_id):
	
	project = get_object_or_404(GivingProject, pk = project_id)
	project_app_list = grants.models.GrantApplication.objects.filter(grant_cycle = project.grant_cycle)
	total_ratings = models.ApplicationRating.objects.filter(membership__giving_project = project, submitted=True)
	dict = {}
	average_points = {}
	member_count = models.Membership.objects.filter(giving_project = project).count()
	
	for rating in total_ratings:
		if dict[rating.application]:
			dict[rating.application].append(rating)
		else:
			dict[rating.application]=[]
			dict[rating.application].append(rating)
    
	for application, reviews in dict:
		grand_total_points = 0
		for review in reviews:
			grand_total_points += review.total()
		average_points[application] = grand_total_points * 1.0 / len(application)
		average_points = sorted(average_points, key=lambda application: average_points[application], reverse=True)
	return render_to_response("scoring/project_summary.html", {"app_list":project_app_list, "dict":dict, "average_points":average_points })
	

	
@login_required(login_url='/fund/login/')
def all_giving_projects(request):	
	all_giving_projects = fund.models.GivingProject.objects.all()
	return render_to_response("scoring/single_giving_project.html", {"projects":all_giving_projects})
	
	
@approved_membership() 
def Save(request):
  logging.info("first")
  if request.method=='POST':
    form = models.RatingForm(request.POST)
    if form.is_valid():
      logging.info('form is valid')
      if not request.is_ajax():
        logging.info('not ajax')
        form.submitted = True
        form.save()
        return redirect('/fund/apps')
      form.save()
      logging.info('INFO SAVED!')
    else:
      logging.info('form is not valid')



  
  return HttpResponse("")


""" There are two blank templates created:
scoring/reading.html
scoring/project_summary.html

Add new ones as needed """
