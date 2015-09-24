from django.db import models

# Create your models here.

class Region(models.Model):
	boundary_polygon = models.FileField()
	pass

class Constraint(models.Model):
	"""

	"""
	enabled = models.BooleanField(default=True)
	name = models.TextField(max_length=255)
	description = models.TextField()
	module_name = models.TextField()  # must match the name of a module in "constraints" module - module must have a class named "Constraint"