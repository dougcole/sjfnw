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
elif os.getenv('SETTINGS_MODE') == 'prod':
  # locally accessing prod DB
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.mysql',
      'HOST': os.getenv('CLOUDSQL_IP'),
      'NAME': 'sjfdb',
      'USER': 'root',
      'PASSWORD': os.getenv('CLOUDSQL_PASSWORD')
    }
  }
elif 'test' in sys.argv:
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.sqlite3'
    }
  }
else:
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.mysql',
      'USER': 'root',
      'PASSWORD': 'SJFdb',
      'HOST': 'localhost',
      'NAME': 'sjfdb_multi',
    }
  }
  DEBUG = True
  # Uncomment below to enable debugging toolbar
  # INSTALLED_APPS.append('django.contrib.staticfiles')
  # INSTALLED_APPS.append('debug_toolbar')

MIDDLEWARE_CLASSES = (
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'sjfnw.fund.middleware.MembershipMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
  'django.contrib.auth.context_processors.auth',
  'django.core.context_processors.request', # only used in fund/base.html js
  'django.contrib.messages.context_processors.messages',
)
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

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
# See maintenance.html. For display only.
MAINTENANCE_END_DISPLAY = ''
