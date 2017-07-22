import os, sys

WSGI_APPLICATION = 'sjfnw.wsgi.application'

ALLOWED_HOSTS = ['.appspot.com']

SECRET_KEY = '*r-$b*8hglm+959&7x043hlm6-&6-3d3vfc4((7yd0dbrakhvi'

INSTALLED_APPS = [
  'django.contrib.auth',
  'django.contrib.admin',
  'django.contrib.contenttypes',
  'django.contrib.humanize',
  'django.contrib.sessions',
  'django.contrib.messages',
  'sjfnw',
  'sjfnw.grants',
  'sjfnw.fund',
  'sjfnw.support',
  'libs.pytz',
]

DEBUG = False
STAGING = False

# deployed
if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine'):
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.mysql',
      'HOST': '/cloudsql/sjf-nw:us-central1:sjfnw',
      'NAME': 'sjfdb',
      'USER': 'root',
      'PASSWORD': os.getenv('CLOUDSQL_PASSWORD')
    }
  }
  if os.getenv('CURRENT_VERSION_ID', '').startswith('staging'):
    STAGING = True
    DATABASES['default']['HOST'] += '-clone-2'

# test
elif 'test' in sys.argv:
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.sqlite3'
    }
  }
# local
else:
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.mysql',
      'USER': 'root',
    }
  }
  if os.getenv('SETTINGS_MODE'):
    DATABASES['default']['HOST'] = os.getenv('CLOUDSQL_IP')
    DATABASES['default']['NAME'] = 'sjfdb'
    DATABASES['default']['PASSWORD'] = os.getenv('CLOUDSQL_PASSWORD')
  else:
    DATABASES['default']['HOST'] = 'localhost'
    DATABASES['default']['NAME'] = 'sjfdb_multi'
    DATABASES['default']['PASSWORD'] = 'SJFdb'
    DEBUG = True
    # Uncomment below to enable debugging toolbar
    INTERNAL_IPS = ['127.0.0.1', '::1']
    INSTALLED_APPS.append('django.contrib.staticfiles')
    INSTALLED_APPS.append('debug_toolbar')

MIDDLEWARE_CLASSES = (
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'debug_toolbar.middleware.DebugToolbarMiddleware',
)

TEMPLATES = [
  {
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'DIRS': (os.path.join(os.path.dirname(__file__), 'templates'),),
    'OPTIONS': {
      'context_processors':  (
        'django.contrib.auth.context_processors.auth',
        'django.template.context_processors.request',
        'django.contrib.messages.context_processors.messages',
      )
    }
  }
]

STATIC_URL = '/static/'

ROOT_URLCONF = 'sjfnw.urls'
APPEND_SLASH = False

LOGGING = {'version': 1}

EMAIL_BACKEND = 'sjfnw.mail.EmailBackend'
EMAIL_QUEUE_NAME = 'default'

USE_TZ = True
TIME_ZONE = 'America/Los_Angeles'

DEFAULT_FILE_STORAGE = 'sjfnw.grants.storage.BlobstoreStorage'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = ('sjfnw.grants.storage.BlobstoreFileUploadHandler',)

TEST_RUNNER = 'sjfnw.tests.base.ColorTestSuiteRunner'

# Determines whether site is in maintenance mode. See urls.py
MAINTENANCE = False
# Date and/or time when site is expected to be out of maintenance mode.
# For display only (does not automatically end maintenance mode)
# See maintenance.html. Example: 'Sunday February 5 at 9:45am PST'
MAINTENANCE_END_DISPLAY = ''
