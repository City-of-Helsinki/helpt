from django.conf import settings
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class ProjectUser(models.Model):
    project = models.ForeignKey(Project, db_index=True, related_name='users')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, related_name='projects')

    def __str__(self):
        return "{} on {}".format(self.user, self.project)
