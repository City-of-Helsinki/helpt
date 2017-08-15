from django.contrib import admin
from .models import GitHubDataSource, Workspace, WorkspaceList, Task, DataSourceUser, TaskAssignment


@admin.register(GitHubDataSource)
class GitHubDataSourceAdmin(admin.ModelAdmin):
    pass


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    pass


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    pass


@admin.register(WorkspaceList)
class WorkspaceList(admin.ModelAdmin):
    pass


@admin.register(DataSourceUser)
class DataSourceUserAdmin(admin.ModelAdmin):
    pass


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    pass
