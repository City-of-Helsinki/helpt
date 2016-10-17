from django.conf import settings
from django.db import models

from .adapters import GitHubAdapter


class DataSource(models.Model):
    TYPES = (
        ('github', 'GitHub'),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPES)

    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through='DataSourceUser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def adapter(self):
        if not hasattr(self, '_adapter'):
            if self.type == 'github':
                self._adapter = GitHubAdapter(self.githubdatasource)
            else:
                raise NotImplementedError('Unknown data source type: {}'.format(self.type))
        return self._adapter

    def __str__(self):
        return self.name


class GitHubDataSource(DataSource):
    client_id = models.CharField(max_length=100)
    client_secret = models.CharField(max_length=100)
    token = models.CharField(max_length=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = 'github'


class DataSourceUser(models.Model):
    data_source = models.ForeignKey(DataSource, db_index=True,
                                    related_name='data_source_users')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True,
                             related_name='data_source_users')

    username = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    origin_id = models.CharField(max_length=100, db_index=True)

    class Meta:
        unique_together = (
            ('data_source', 'user'),
            ('data_source', 'username'),
            ('data_source', 'origin_id'),
        )

    def __str__(self):
        return "{}: {} as {}".format(self.data_source, self.user, self.origin_id)


class Project(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class ProjectUser(models.Model):
    project = models.ForeignKey(Project, db_index=True, related_name='users')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, related_name='projects')

    def __str__(self):
        return "{} on {}".format(self.user, self.project)


class Workspace(models.Model):
    data_source = models.ForeignKey(DataSource, db_index=True,
                                    related_name='workspaces')
    project = models.ForeignKey(Project, db_index=True,
                                related_name='workspaces')
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    origin_id = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return self.name

    def sync_tasks(self):
        adapter = self.data_source.adapter
        adapter.sync_tasks(self)


class TaskQuerySet(models.QuerySet):
    def open(self):
        return self.filter(state='open')

    def closed(self):
        return self.filter(state='closed')


class Task(models.Model):
    STATE_OPEN = 'open'
    STATE_CLOSED = 'closed'

    STATES = (
        (STATE_OPEN, 'open'),
        (STATE_CLOSED, 'closed')
    )

    name = models.CharField(max_length=200)
    workspace = models.ForeignKey(Workspace, db_index=True, related_name='tasks')
    origin_id = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=10, choices=STATES, db_index=True)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    assigned_users = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                            through='TaskAssignment',
                                            blank=True)

    objects = TaskQuerySet.as_manager()

    def __str__(self):
        return "{} ({})".format(self.name, self.workspace)

    def set_state(self, new_state):
        """
        Set the state of this task, verifying valid values

        :param new_state: Requested state for this task
        """
        if new_state == self.state:
            return

        assert new_state in [x[0] for x in self.STATES]
        self.state = new_state
        # FIXME, inquire why the model is saved here
        # (update_fields precludes using this for new models)
#        self.save(update_fields=['state'])

    class Meta:
        ordering = ['workspace', 'origin_id']
        unique_together = [('workspace', 'origin_id')]
        get_latest_by = 'created_at'


class TaskAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='task_assignments',
                             db_index=True)
    task = models.ForeignKey(Task, related_name='assignments', db_index=True)

    def __str__(self):
        return "{} assigned to {}".format(self.task, self.user)

    class Meta:
        unique_together = [('user', 'task')]
