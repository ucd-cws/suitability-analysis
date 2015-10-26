"""
	Celery tasks for server. Likely to be controller functions initiating a suitability analysis
"""

__author__ = 'nickrsan'

from FloodMitigation.celery import app as celery_app