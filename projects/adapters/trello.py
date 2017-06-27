from .base import Adapter

# To handle import of Workspace, that imports GithubAdapter
from django.apps import apps

# To call the Trello API
import requests

import logging

logger = logging.getLogger(__name__)


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

    def _import_board(self, board):
        data = dict(name=board['name'], description=None, origin_id=board['id'])
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
        )

    def sync_workspaces(self):
        organization = self.data_source.organization
        data = self.api_get('organizations/%s/boards' % organization,
                            memberships_member='true')
        workspaces = [self._import_board(board) for board in data]
        self._update_workspaces(workspaces)

    def _create_user(self, workspace, assignee):
        logger.debug("new user: {}".format(assignee['id']))
        ds = workspace.data_source
        m = apps.get_model(app_label='projects', model_name='DataSourceUser')
        return m.objects.create(origin_id=assignee['id'],
                                data_source=ds,
                                username=assignee['login'])

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


        obj.save()

        assignees = task['assignees']

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
