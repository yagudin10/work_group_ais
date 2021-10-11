from django.db import models
from django.db.models.base import Model

# Create your models here.
class MFC(models.Model):
    name = models.CharField(max_length=100)