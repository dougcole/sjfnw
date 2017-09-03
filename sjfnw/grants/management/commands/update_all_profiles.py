from django.core.management.base import BaseCommand
from django.conf import settings

from sjfnw.grants.models import Organization

class Command(BaseCommand):

  help = ('Update org profiles.')

  def handle(self, *args, **kwargs): # pylint: disable=unused-argument

    self.stdout.write('Using ' + settings.DATABASES['default']['NAME'])
    confirm = raw_input('Continue? (y/n) ')
    if confirm != 'y':
      self.stdout.write('Aborting')
      return

    orgs = Organization.objects.all()

    for org in orgs:
      apps = org.grantapplication_set.order_by('-submission_time')
      if len(apps) > 0:
        app = apps[0]
        # pylint: disable=protected-access
        for field in [f.name for f in Organization._meta.get_fields()]:
          if field != 'id' and hasattr(app, field):
            setattr(org, field, getattr(app, field))
        org.save()
        self.stdout.write('Updated organization profile for ' + org.name)
      else:
        self.stdout.write('Skipping %s, no applications submitted' % org.name)

    self.stdout.write('All org profiles updated.')
