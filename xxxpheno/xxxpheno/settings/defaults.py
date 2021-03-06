"""
Django settings for project.

Generated by 'django-admin startproject' using Django 1.9.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__+ "/../")))

# Load values hidden from GitHub
from private_settings import *

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'

# Application settings, used in application_context() in xxxpheno/home/views.py
APP_PREFIX = 'Arachis'
APP_NAME = APP_PREFIX + 'Pheno'
APP_NAME_LOWER = APP_NAME.lower()
APP_SPECIES = 'peanut'
APP_BACKGROUND_IMAGE = APP_NAME_LOWER + '_background.jpg'
APP_CSS_FILENAME = APP_NAME_LOWER + '.css'
APP_TITLE_BACKGROUND_COLOR = '#4D0D00'
APP_TITLE_WIDTH = '275px'
APP_TITLE_ICON = 'peanutbase_logo.png'
APP_TITLE_ICON_WIDTH = 49
APP_TITLE_ICON_HEIGHT = 42
APP_TWITTER_FEED = 'https://twitter.com/peanutbaseorg'
APP_TWITTER_TEXT = 'Tweets by PeanutBase'
APP_CORRELATION_PHENOTYPE_IDS = '2,3,5,7,11,13,17,19,23,29'

EMAIL_HOST = 'hardy.lis.ncgr.org'
EMAIL_PORT = 25
EMAIL_ADDRESS = 'peanutbase-contact@iastate.edu' # for sending submission status, etc

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY','REPLACE_WITH_PROD_KEY')


ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS','dev-arachispheno').split()

# Application definition

INSTALLED_APPS = [
    'autocomplete_light',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'home',
    'phenotypedb',
    'django_tables2',
    'rest_framework',
    'rest_framework_swagger',
    'widget_tweaks',
    'corsheaders',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
        'rest_framework.permissions.DjangoModelPermissions',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        #'rest_framework.renderers.BrowsableAPIRenderer',
        #can be added if necessary (provides a nice browser interface)
        'rest_framework_csv.renderers.CSVRenderer',
        'rest_framework.renderers.JSONRenderer',
        'phenotypedb.renderer.PLINKRenderer',
    ),
}

MIDDLEWARE_CLASSES = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'xxxpheno.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, '../html'), os.path.join(BASE_DIR,'../xml/')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'phenotypedb.context_processors.version',
            ],
        },
    },
]

WSGI_APPLICATION = 'xxxpheno.wsgi.application'





# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/srv/static'


STATICFILES_DIRS = [os.path.join(BASE_DIR,'../static'),]

# https://github.com/marcgibbons/django-rest-swagger/issues/220
# Needed to get     request.is_secure() == True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

GITHUB_URL='https://github.com/legumeinfo/' + APP_NAME + '/commit'
DATACITE_PREFIX = '10.21958' # TODO: this is for AraPheno, change it to ours
DATACITE_USERNAME = os.environ.get('DATACITE_USERNAME', None)
DATACITE_PASSWORD = os.environ.get('DATACITE_PASSWORD', None)
DATACITE_DOI_URL = 'http://search.datacite.org/works'
DOI_BASE_URL = BASE_URL


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}

CORS_ORIGIN_WHITELIST = (
    BASE_URL,
    'http://localhost:8000',
    'http://localhost:8080',
    'http://127.0.0.1:8080'
)
