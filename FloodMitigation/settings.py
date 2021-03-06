"""
Django settings for FloodMitigation project.

Generated by 'django-admin startproject' using Django 1.8.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

from FloodMitigation.local_settings import *

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'relocation',
	'census_search',
)

MIDDLEWARE_CLASSES = (
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'FloodMitigation.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'FloodMitigation.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {
		'simple': {
			'format': '%(levelname)s %(message)s'
		},
	},
	'handlers': {
		'log_to_stdout': {
			'level': 'DEBUG',
			'class': 'logging.StreamHandler',
			'formatter': 'simple',
			},
		'log_to_file': {
			'level': 'DEBUG',
			'class': 'logging.FileHandler',
			'formatter': 'simple',
			'filename': os.path.join(BASE_DIR, 'relocation.log'),
			},
		},
	'loggers': {
		'geoprocessing_log': {
			'handlers': ['log_to_stdout'],
			'level': 'DEBUG',
			'propagate': True,
		},
		'processing_log': {
			'handlers': ['log_to_stdout'],
			'level': 'DEBUG',
			'propagate': True,
		},
		'geoprocessing': {
			'handlers': ['log_to_stdout'],
			'level': 'DEBUG',
			'propagate': True,
		},
		'main': {
			'handlers': ['log_to_stdout'],
			'level': 'DEBUG',
			'propagate': True,
		},
		'silent_error_log': {
			'handlers': ['log_to_file'],
			'level': 'DEBUG',
			'propagate': True,
		}
	}
}
