from django.db import models

class Place(models.Model):
    key = models.IntegerField
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)

    def __str__(self):
        return self.city