from django.db import models
from helusers.models import AbstractUser


class Organization(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return self.name


class User(AbstractUser):
    organization = models.ForeignKey(Organization, db_index=True, null=True, blank=True)

    class Meta:
        ordering = ('id',)
