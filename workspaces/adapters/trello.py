import requests
import logging
import json
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
        assert resp.status_code == 200
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
            raise TrelloAPIException('POST failed with %d: "%s"' % (
                resp.status_code, resp.content.decode('utf8')
            ))

    def _import_list(self, lst):
        data = dict(name=lst['name'], origin_id=lst['id'], position=lst['pos'])
        if lst['closed']:
            state = 'closed'
        else:
            state = 'open'
        data['state'] = state
        return data

    def _import_board(self, board):
        data = dict(name=board['name'], description=None, origin_id=board['id'])
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

    def sync_workspaces(self):
        organization = self.data_source.organization
        data = self.api_get('organizations/%s/boards' % organization,
                            memberships_member='true', lists='open')
        workspaces = [self._import_board(board) for board in data]
        self._update_workspaces(workspaces)

    def register_workspace_webhook(self, workspace, callback_url):
        data = dict(
            description="%s listener" % workspace.name,
            idModel=workspace.origin_id,
            callbackURL=callback_url
        )
        self.api_post('tokens/%s/webhooks/' % self.data_source.token, data=json.dumps(data))

    def _create_user(self, workspace, assignee):
        logger.debug("new user: {}".format(assignee['id']))
        ds = workspace.data_source
        m = apps.get_model(app_label='workspaces', model_name='DataSourceUser')
        return m.objects.create(origin_id=assignee['id'],
                                data_source=ds,
                                username=assignee['login'])

    def sync_tasks(self, workspace):
        """
        Synchronize tasks between given workspace and its Trello source
        :param workspace: Workspace to be synced
        """

        data = self.api_get('boards/{}/cards'.format(workspace.origin_id),
                            member_fields='username,fullName', members='true')
        all_members = {}
        for card in data:
            for member in card['members']:
                if member['id'] in all_members:
                    continue
                all_members[member['id']] = member

        users = [self._import_user(user) for user in all_members.values()]
        self.save_users(users)
        tasks = [self._import_card(card) for card in data]
        super()._update_tasks(workspace, tasks)
