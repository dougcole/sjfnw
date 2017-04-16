from sjfnw.fund.models import Member

def get_viewing_permission(user, application):
  """ Return a number indicating viewing permission for a submitted app.

      Args:
        user: django user object
        application: GrantApplication

      Returns:
        0 - anon viewer or member without permission to view
        1 - member with permission to view
        2 - staff
        3 - app creator
  """
  if user.is_staff:
    return 2
  elif user == getattr(application.organization, 'user', None):
    return 3
  else:
    try:
      member = Member.objects.select_related().get(user=user)
      for ship in member.membership_set.all():
        if ship.giving_project in application.giving_projects.all():
          return 1
      return 0
    except Member.DoesNotExist:
      return 0
