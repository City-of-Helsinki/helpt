from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from projects.models import Project
from .adapters import GitHubAdapter, TrelloAdapter


class DataSource(models.Model):
    TYPES = (
        ('github', 'GitHub'),
        ('trello', 'Trello')
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
            elif self.type == 'trello':
                self._adapter = TrelloAdapter(self.trellodatasource)
            else:
                raise NotImplementedError('Unknown data source type: {}'.format(self.type))
        return self._adapter

    def __str__(self):
        return self.name

    def sync_workspaces(self):
        adapter = self.adapter
        adapter.sync_workspaces()

    def sync_data_source(self):
        adapter = self.adapter
        adapter.sync_data_source()


class GitHubDataSource(DataSource):
    """
    GitHubDataSource is a container for GitHub-specific authentication
    information. If that is not needed, it merely indicates that the
    Datasource gets its information from GitHub
    """
    client_id = models.CharField(max_length=100, blank=True, null=True)
    client_secret = models.CharField(max_length=100, blank=True, null=True)
    token = models.CharField(max_length=100, blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = 'github'


class TrelloDataSource(DataSource):
    """
    TrelloDataSource is a container for Trello-specific authentication
    information.
    """
    key = models.CharField(max_length=100)
    token = models.CharField(max_length=100)
    organization = models.CharField(_('Trello organization ID'), max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = 'trello'


class DataSourceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(state='active')

    def inactive(self):
        return self.filter(state='inactive')


class DataSourceUser(models.Model):
    STATE_ACTIVE = 'active'
    STATE_INACTIVE = 'inactive'

    STATES = (
        (STATE_ACTIVE, _('active')),
        (STATE_INACTIVE, _('inactive'))
    )

    data_source = models.ForeignKey(DataSource, db_index=True,
                                    related_name='data_source_users')
    # Link to local user may be null. It is the responsibility of the
    # adapter to fill this in when the user first logs in here.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True,
                             related_name='data_source_users',
                             on_delete=models.SET_NULL,
                             blank=True, null=True)

    username = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    origin_id = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=10, choices=STATES, db_index=True,
                             default=STATE_ACTIVE)

    objects = DataSourceQuerySet.as_manager()

    def __str__(self):
        return "{}: {} -> {}".format(self.data_source, self.username, self.user)

    def set_state(self, new_state):
        """
        Set the state of this data source user, verifying valid values

        :param new_state: New state
        """
        if new_state == self.state:
            return

        assert new_state in [x[0] for x in self.STATES]
        self.state = new_state
        self.save(update_fields=['state'])

    class Meta:
        unique_together = (
            ('data_source', 'user'),
            ('data_source', 'username'),
            ('data_source', 'origin_id'),
        )


class WorkspaceQuerySet(models.QuerySet):
    def open(self):
        return self.filter(state='open')

    def closed(self):
        return self.filter(state='closed')


class Workspace(models.Model):
    STATE_OPEN = 'open'
    STATE_CLOSED = 'closed'

    STATES = (
        (STATE_OPEN, _('open')),
        (STATE_CLOSED, _('closed'))
    )

    data_source = models.ForeignKey(DataSource, db_index=True,
                                    related_name='workspaces')
    projects = models.ManyToManyField(Project, db_index=True,
                                      related_name='workspaces')
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    origin_id = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=10, choices=STATES, db_index=True,
                             default=STATE_OPEN)

    objects = WorkspaceQuerySet.as_manager()

    def __str__(self):
        return "%s / %s" % (self.data_source, self.name)

    def sync_tasks(self):
        adapter = self.data_source.adapter
        adapter.sync_tasks(self)

    class Meta:
        unique_together = [('data_source', 'origin_id')]
        get_latest_by = 'created_at'


class TrelloWorkspace(Workspace):
    in_progress_list = models.CharField(max_length=100)


class TaskQuerySet(models.QuerySet):
    def open(self):
        return self.filter(state='open')

    def closed(self):
        return self.filter(state='closed')


class Task(models.Model):
    STATE_OPEN = 'open'
    STATE_CLOSED = 'closed'

    STATES = (
        (STATE_OPEN, _('open')),
        (STATE_CLOSED, _('closed'))
    )

    name = models.CharField(max_length=200)
    workspace = models.ForeignKey(Workspace, db_index=True, related_name='tasks')
    origin_id = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=10, choices=STATES, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    assigned_users = models.ManyToManyField(DataSourceUser,
                                            through='TaskAssignment',
                                            blank=True)

    objects = TaskQuerySet.as_manager()

    def __str__(self):
        return "{} ({})".format(self.name, self.workspace)

    def set_state(self, new_state, save=True):
        """
        Set the state of this task, verifying valid values

        :param new_state: Requested state for this task
        """
        if new_state == self.state:
            return

        assert new_state in [x[0] for x in self.STATES]
        self.state = new_state
        if save:
            self.save(update_fields=['state'])

    class Meta:
        ordering = ['workspace', 'origin_id']
        unique_together = [('workspace', 'origin_id')]
        get_latest_by = 'created_at'


class TaskAssignment(models.Model):
    user = models.ForeignKey(DataSourceUser, related_name='task_assignments',
                             db_index=True)
    task = models.ForeignKey(Task, related_name='assignments', db_index=True)

    def __str__(self):
        return "{} assigned to {}".format(self.task, self.user)

    class Meta:
        unique_together = [('user', 'task')]