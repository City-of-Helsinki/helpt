from django.contrib import admin
from .models import GitHubDataSource, Project, Workspace, Task, ProjectUser, DataSourceUser


@admin.register(GitHubDataSource)
class GitHubDataSourceAdmin(admin.ModelAdmin):
    pass


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    pass

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    pass

@admin.register(ProjectUser)
class ProjectUserAdmin(admin.ModelAdmin):
    pass

@admin.register(DataSourceUser)
class DataSourceUserAdmin(admin.ModelAdmin):
    pass
