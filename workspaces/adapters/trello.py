import requests
import logging
import json
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf.urls import url
from django.apps import apps

from .base import Adapter

logger = logging.getLogger(__name__)


class TrelloAPIException(Exception):
    pass


class TrelloAdapter(Adapter):
    API_BASE = 'https://api.trello.com/1/'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def api_get(self, path, **kwargs):
        url = self.API_BASE + path
        params = dict(key=self.data_source.key, token=self.data_source.token)
        params.update(kwargs)
        resp = requests.get(url, params=params)
        assert resp.status_code == 200, "Trello API error: %s" % resp.content
        return resp.json()

    def api_delete(self, path, **kwargs):
        url = self.API_BASE + path
        params = dict(key=self.data_source.key, token=self.data_source.token)
        params.update(kwargs)
        resp = requests.delete(url, params=params)
        assert resp.status_code == 200, "Trello API error: %s" % resp.content
        return resp.json()

    def api_post(self, path, **kwargs):
        url = self.API_BASE + path

        params = dict(key=self.data_source.key, token=self.data_source.token)
        post_kwargs = {}
        if 'data' in kwargs:
            post_kwargs['data'] = kwargs.pop('data')
            post_kwargs['params'] = params
        params.update(kwargs)

        post_kwargs['headers'] = {'Content-type': 'application/json'}
        resp = requests.post(url, **post_kwargs)
        if resp.status_code != 200:
            raise TrelloAPIException("POST failed with %d: \"%s\"" % (
                resp.status_code, resp.content.decode('utf8')
            ))
        return resp.json()

    def _import_list(self, lst):
        data = dict(name=lst['name'], origin_id=lst['id'], position=lst['pos'])
        if lst['closed']:
            state = 'closed'
        else:
            state = 'open'
        data['state'] = state
        return data

    def _import_board(self, board):
        data = dict(name=board['name'], description=None, origin_id=board['id'], url=board['url'])
        data['lists'] = [self._import_list(l) for l in board['lists']]
        return data

    def _import_user(self, user):
        return dict(username=user['username'], origin_id=user['id'], full_name=user['fullName'])

    def _import_card(self, card):
        if card['closed']:
            state = 'closed'
        else:
            state = 'open'
        return dict(
            origin_id=card['id'],
            state=state,
            assigned_users=card['idMembers'],
            updated_at=card['dateLastActivity'],
            name=card['name'],
            position=card['pos'],
            list_origin_id=card['idList']
        )

    def sync_workspaces(self, origin_id=None):
        if not origin_id:
            organization = self.data_source.organization
            data = self.api_get('organizations/%s/boards' % organization,
                                memberships_member='true', lists='open')
            workspaces = [self._import_board(board) for board in data]
            self._update_workspaces(workspaces)
        else:
            data = self.api_get('boards/%s' % origin_id, memberships_member='true',
                                lists='open')
            self._update_workspaces(self._import_board(data))

    def register_workspace_webhook(self, workspace, callback_url):
        data = dict(
            description="%s listener" % workspace.name,
            idModel=workspace.origin_id,
            callbackURL=callback_url
        )
        self.api_post('tokens/%s/webhooks/' % self.data_source.token, data=json.dumps(data))

    def clear_webhooks(self):
        data = self.api_get('tokens/%s/webhooks' % self.data_source.token)
        for hook in data:
            self.api_delete('tokens/%s/webhooks/%s' % (self.data_source.token, hook['id']))

    def remove_webhook(self, origin_id):
        with transaction.atomic():
            self.delete_webhook(origin_id)
            self.api_delete('tokens/{}/webhooks/{}'.format(self.data_source.token, origin_id))

    def sync_tasks(self, workspace, origin_id=None):
        """
        Synchronize tasks between given workspace and its Trello source
        :param workspace: Workspace to be synced
        :param origin_id: Task id if only one task is to be synced
        """

        if not origin_id:
            data = self.api_get('boards/{}/cards'.format(workspace.origin_id),
                                member_fields='username,fullName', members='true')
        else:
            card = self.api_get('cards/{}'.format(origin_id),
                                member_fields='username,fullName', members='true')
            data = [card]

        tasks = [self._import_card(card) for card in data]
        all_members = {}
        for card in data:
            for member in card['members']:
                if member['id'] in all_members:
                    continue
                all_members[member['id']] = member

        users = [self._import_user(user) for user in all_members.values()]
        self.save_users(users)

        if not origin_id:
            self._update_tasks(workspace, tasks)
        else:
            self._update_tasks(workspace, tasks[0])


def handle_trello_event(event):
    Workspace = apps.get_model(app_label='workspaces', model_name='Workspace')

    board_id = event['model']['id']
    workspace = Workspace.objects.get(data_source__type='trello', origin_id=board_id)
    action = event['action']
    if 'card' in action['data']:
        card_id = action['data']['card']['id']
        workspace.schedule_task_sync(card_id)
    elif 'list' in action['data']:
        workspace.schedule_sync()

    return HttpResponse()


@csrf_exempt
@require_http_methods(['HEAD', 'GET', 'POST'])
def receive_trello_hook(request):
    if request.method in ('HEAD', 'GET'):
        return HttpResponse()

    try:
        event = json.loads(request.body.decode("utf-8"))
    # What's the exception for invalid utf-8?
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON received")
    except UnicodeError:
        return HttpResponseBadRequest("Invalid character encoding, expecting UTF-8")

    action_type = event.get('action', {}).get('type', '[unknown]')
    logger.info("Received Trello event %s for workspace %s" % (
        action_type, event.get('model', {}).get('name')
    ))

    try:
        resp = handle_trello_event(event)
    except Exception as e:
        logger.exception("Trello event handling failed")
        # In case of internal error, still reply with HTTP 200 so that
        # Trello won't get annoyed.
        return HttpResponse("Server error")
    return resp


urls = [url(r'^$', receive_trello_hook, name='trello-webhook')]
