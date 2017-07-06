from django.contrib import admin
from .models import Project, ProjectUser


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectUser)
class ProjectUserAdmin(admin.ModelAdmin):
    pass
