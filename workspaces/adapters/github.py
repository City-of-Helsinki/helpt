import requests
import logging
import json

from django.db import transaction
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf.urls import url

from .base import Adapter


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
            assert resp.status_code == 200, "GitHub API error: %s" % resp.json()['message']
            data = resp.json()
            next_link = resp.links.get('next')
            if isinstance(data, list):
                objs += data
            else:
                assert not next_link
                return data
            if not next_link:
                break
            url = next_link['url']

        return objs

    def api_post(self, path, **kwargs):
        if self.data_source.token:
            headers = {'Authorization': 'token {}'.format(self.data_source.token)}
        else:
            headers = None
        url = self.API_BASE + path
        resp = requests.post(url, headers=headers, **kwargs)
        data = resp.json()
        assert resp.status_code == 201, "GitHub API error: %s" % data['message']
        return data

    def api_delete(self, path, **kwargs):
        if self.data_source.token:
            headers = {'Authorization': 'token {}'.format(self.data_source.token)}
        else:
            headers = None
        url = self.API_BASE + path
        resp = requests.delete(url, headers=headers, **kwargs)
        assert resp.status_code in (200, 204), "GitHub API error: %s" % resp.json()['message']

    def _import_repo(self, data):
        ret = dict(name=data['name'], description=data['description'], origin_id=str(data['id']),
                   state='open')
        return ret

    def _import_issue(self, data):
        assert data['state'] in ('open', 'closed')
        return dict(
            origin_id=str(data['number']),
            state=data['state'],
            assigned_users=[str(u['id']) for u in data['assignees']],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            closed_at=data['closed_at'],
            name=data['title'],
        )

    def _import_user(self, data):
        return dict(username=data['login'], origin_id=str(data['id']))

    def sync_workspaces(self, origin_id=None):
        if not origin_id:
            organization = self.data_source.organization
            data = self.api_get('orgs/%s/repos' % organization)
            workspaces = [self._import_repo(repo) for repo in data]
            self._update_workspaces(workspaces)
        else:
            data = self.api_get('repos/%s' % origin_id)
            self._update_workspaces(self._import_repo(data))

    def sync_tasks(self, workspace, origin_id=None):
        """
        Synchronize tasks between given workspace and its Trello source
        :param workspace: Workspace to be synced
        :param origin_id: Task id if only one task is to be synced
        """

        repo_part = '{}/{}'.format(self.data_source.organization, workspace.name)
        if not origin_id:
            data = self.api_get('repos/{}/issues'.format(repo_part), state='all')
        else:
            card = self.api_get('repos/{}/issues/{}'.format(repo_part, origin_id))
            data = [card]

        tasks = [self._import_issue(card) for card in data]
        all_users = {}
        for issue in data:
            for user in issue['assignees']:
                if user['id'] in all_users:
                    continue
                all_users[user['id']] = user

        users = [self._import_user(user) for user in all_users.values()]
        self.save_users(users)

        if not origin_id:
            self._update_tasks(workspace, tasks)
        else:
            self._update_tasks(workspace, tasks[0])

    def register_webhook(self, callback_url):
        config = dict(url=callback_url, content_type='json')
        data = dict(name='web', events=['issues', 'repository'], active=True, config=config)
        ret = self.api_post('orgs/{}/hooks'.format(self.data_source.organization), data=json.dumps(data))
        self.save_webhook(dict(origin_id=str(ret['id'])))

    def remove_webhook(self, origin_id):
        with transaction.atomic():
            self.delete_webhook(origin_id)
            self.api_delete('orgs/{}/hooks/{}'.format(self.data_source.organization, origin_id))


def handle_github_event(event_type, event):
    GitHubDataSource = apps.get_model(app_label='workspaces', model_name='GitHubDataSource')
    ds = GitHubDataSource.objects.get(organization=event['organization']['login'])

    if event_type == 'issues':
        ws = ds.workspaces.get(origin_id=event['repository']['id'])
        issue_id = str(event['issue']['number'])
        ws.schedule_task_sync(issue_id)
    elif event_type == 'repository':
        ds.schedule_workspace_sync()

    return HttpResponse('OK')


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

    if event_type not in ("issues", "repository"):
        return HttpResponseBadRequest("Event type is not \"issues\". Bad hook configuration?")

    try:
        event = json.loads(request.body.decode("utf-8"))
    # What's the exception for invalid utf-8?
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON received")
    except UnicodeError:
        return HttpResponseBadRequest("Invalid character encoding, expecting UTF-8")

    try:
        resp = handle_github_event(event_type, event)
    except Exception as e:
        logger.exception("GitHub event handling failed")
        # In case of internal error, still reply with HTTP 200 so that
        # GitHub is happy. We're logging the exception to Sentry anyway.
        return HttpResponse("Server error")
    return resp


urls = [url(r'^$', receive_github_hook)]
