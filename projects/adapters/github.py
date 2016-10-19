from .base import Adapter
from .sync import ModelSyncher

# To handle import of Workspace, that imports GithubAdapter
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf.urls import url
import json

# To call Github API
import requests
import requests_cache

import logging

requests_cache.install_cache('github')

logger = logging.getLogger(__name__)

class GitHubAdapter(Adapter):
    API_BASE = 'https://api.github.com/'

    def api_get(self, path, **kwargs):
        # GitHub does not always require authorization
        if self.data_source.token:
            headers = {'Authorization': 'token {}'.format(self.data_source.token)}
        else:
            headers = None
        url = self.API_BASE + path
        objs = []
        while True:
            resp = requests.get(url, headers=headers, params=kwargs)
            assert resp.status_code == 200
            objs += resp.json()
            next_link = resp.links.get('next')
            if not next_link:
                break
            url = next_link['url']

        return objs

    def sync_workspaces(self):
        pass

    def update_task(self, obj, task, users_by_id):
        """
        Update a Task object with data from Github issue

        :param obj: Task object that should be updated
        :param task: Github issue structure, as used in Github APIs
        :param users_by_id: List of local users for task assignment
        """
        obj.name = task['title']
        for f in ['created_at', 'updated_at', 'closed_at']:
            setattr(obj, f, task[f])

        obj.set_state(task['state'])

        obj.save()

        assignees = task['assignees']
        new_assignees = set()
        for assignee in assignees:
            user = users_by_id.get(assignee['id'])
            if not user:
                continue
            new_assignees.add(user)
        old_assignees = set([x.user for x in obj.assignments.all()])

        for user in new_assignees - old_assignees:
            obj.assignments.create(user=user)
        remove_assignees = old_assignees - new_assignees
        if remove_assignees:
            obj.assignments.filter(user__in=remove_assignees).delete()

        logger.debug('#{}: [{}] {}'.format(task['number'], task['state'], task['title']))

    def _get_users_by_id(self):
        data_source_users = self.data_source.data_source_users.all()
        return {int(u.origin_id): u.user for u in data_source_users}

    def sync_tasks(self, workspace):
        """
        Synchronize tasks between given workspace and its GitHub source
        :param workspace: Workspace to be synced
        """

        def close_task(task):
            logger.debug("Marking %s closed" % task)
            task.set_state('closed')

        data = self.api_get('repos/{}/issues'.format(workspace.origin_id))

        users_by_id = self._get_users_by_id()

        Task = workspace.tasks.model

        syncher = ModelSyncher(workspace.tasks.open(),
                               lambda task: int(task.origin_id),
                               delete_func=close_task)

        for task in data:
            obj = syncher.get(task['number'])
            if not obj:
                obj = Task(workspace=workspace, origin_id=task['number'])

            syncher.mark(obj)
            self.update_task(obj, task, users_by_id)

        syncher.finish()

@csrf_exempt
@require_POST
def receive_github_hook(request):
    # TODO: Verify IP whitelist
    # TODO: Verify shared secret
    try:
        event_type = request.META['HTTP_X_GITHUB_EVENT']
    except KeyError:
        return HttpResponseBadRequest("GitHub event type missing")

    # Respond to GitHub ping event, not really necessary, but cute
    if event_type == "ping":
        return HttpResponse("pong")

    if event_type != "issues":
        return HttpResponseBadRequest("Event type is not \"issues\". Bad hook configuration?")

    try:
        event = json.loads(request.body.decode("utf-8"))
    # What's the exception for invalid utf-8?
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON received")
    except UnicodeError:
        return HttpResponseBadRequest("Invalid character encoding, expecting UTF-8")

    # Task management only cares about GitHub issues
    if 'issue' in event:
        issue_identifier = event['issue']['number']
    else:
        return HttpResponseBadRequest("Issue structure missing. Bad hook configuration?")

    if 'repository' in event:
        event_origin = event['repository']['full_name']
    else:
        return HttpResponseBadRequest("Repository information missing, should be included with issue")

    # Work around circular imports
    Workspace = apps.get_model(app_label='projects', model_name='Workspace')
    GitHubDataSource = apps.get_model(app_label='projects', model_name='GitHubDataSource')
    Project = apps.get_model(app_label='projects', model_name='Project')

    try:
        workspace = Workspace.objects.get(origin_id=event_origin)
    except Workspace.DoesNotExist:
        # New workspaces get 'unassigned' project and generic github
        project, _ = Project.objects.get_or_create(name='Unassigned')
        data_source, _ = GitHubDataSource.objects.get_or_create(name="GitHub")

        name = event['repository']['name']
        description = event['repository']['description']
        workspace = Workspace.objects.create(origin_id=event_origin,
                                             name=name,
                                             description=description,
                                             data_source=data_source,
                                             project=project)

    # Tasks must be fetched through workspaces, as their identifiers
    # are only unique within workspace
    Task = workspace.tasks.model
    try:
        task = workspace.tasks.get(origin_id=issue_identifier)
    except Task.DoesNotExist:
        task = Task(workspace=workspace, origin_id=issue_identifier)

    adapter = workspace.data_source.adapter

    users_by_id = adapter._get_users_by_id()

    adapter.update_task(task, event['issue'], users_by_id)

    return HttpResponse("processed, acted on")

urls = [url(r'$^', receive_github_hook)]
