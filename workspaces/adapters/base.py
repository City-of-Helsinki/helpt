import logging

from .sync import ModelSyncher


logger = logging.getLogger(__name__)


class Adapter(object):
    def __init__(self, data_source):
        self.data_source = data_source

    def _update_workspace_lists(self, workspace, lists):
        def close_list(lst):
            if lst.state == lst.STATE_CLOSED:
                return
            logger.debug("Marking list %s closed" % lst)
            lst.set_state('closed')

        WorkspaceList = workspace.lists.model
        syncher = ModelSyncher(workspace.lists.all(),
                               lambda lst: lst.origin_id,
                               delete_func=close_list)

        for lst in lists:
            obj = syncher.get(lst['origin_id'])
            if not obj:
                obj = WorkspaceList(workspace=workspace, origin_id=lst['origin_id'])
            for attr_name, value in lst.items():
                if attr_name == 'state':
                    continue
                setattr(obj, attr_name, value)
            if not obj.id:
                logger.debug('Creating new workspace list: %s' % obj)
                created = True
            else:
                created = False
            if not obj.task_state and workspace.default_list_task_state:
                obj.task_state = workspace.default_list_task_state
            obj.save()
            if created and 'state' in lst:
                obj.set_state(lst['state'])
            syncher.mark(obj)

        syncher.finish()

    def _update_workspaces(self, workspace_or_workspaces):
        """
        Synchronizes workspace database based on supplied data dicts
        """
        def close_workspace(ws):
            if ws.state == ws.STATE_CLOSED:
                return
            logger.debug("Marking workspace %s closed" % ws)
            ws.set_state('closed')

        if isinstance(workspace_or_workspaces, dict):
            workspaces = [workspace_or_workspaces]
            skip_delete = True
        else:
            workspaces = workspace_or_workspaces
            skip_delete = False

        # Get access to model through trickery because otherwise
        # there would be a circular import.
        Workspace = self.data_source.workspaces.model
        syncher = ModelSyncher(self.data_source.workspaces.open(),
                               lambda ws: ws.origin_id,
                               delete_func=close_workspace,
                               skip_delete=skip_delete)

        for ws in workspaces:
            obj = syncher.get(ws['origin_id'])
            if not obj:
                obj = Workspace(data_source=self.data_source, origin_id=ws['origin_id'])
            ws_lists = ws.pop('lists', [])
            for attr_name, value in ws.items():
                if attr_name == 'state':
                    continue
                setattr(obj, attr_name, value)
            if not obj.id:
                logger.debug('Creating new workspace: %s' % obj)
                created = True
            else:
                created = False
            obj.save()
            if created and 'state' in ws:
                obj.set_state(ws['state'])
            self._update_workspace_lists(obj, ws_lists)
            syncher.mark(obj)

        syncher.finish()

    def _update_tasks(self, workspace, task_or_tasks):
        def close_task(task):
            logger.debug("Marking %s closed" % task)
            task.set_state('closed')

        skip_delete = False
        if isinstance(task_or_tasks, dict):
            tasks = [task_or_tasks]
            skip_delete = True
        else:
            tasks = task_or_tasks

        users = self.data_source.data_source_users.all().select_related('user')
        users_by_id = {u.origin_id: u for u in users}

        lists_by_id = {l.origin_id: l for l in workspace.lists.all()}

        Task = workspace.tasks.model
        syncher = ModelSyncher(workspace.tasks.all(),
                               lambda task: task.origin_id,
                               delete_func=close_task,
                               skip_delete=skip_delete)
        for task in tasks:
            task = task.copy()
            task_id = task.pop('origin_id')
            obj = syncher.get(task_id)
            if not obj:
                obj = Task(workspace=workspace, origin_id=task_id)

            syncher.mark(obj)
            task_state = task.pop('state', None)

            assigned_users = task.pop('assigned_users')

            list_id = task.pop('list_origin_id', None)
            obj.list = lists_by_id.get(list_id)

            for attr_name, value in task.items():
                setattr(obj, attr_name, value)

            if obj.list and obj.list.task_state:
                task_state = obj.list.task_state

            obj.set_state(task_state, save=False)
            obj.save()

            new_assignees = set()
            for user_id in assigned_users:
                user = users_by_id.get(user_id)
                if not user:
                    logger.error('Task %s: user with id %s not found' % (task_id, user_id))
                    continue
                new_assignees.add(user)
            old_assignees = set([x.user for x in obj.assignments.all()])

            for user in new_assignees - old_assignees:
                obj.assignments.create(user=user)
            remove_assignees = old_assignees - new_assignees
            if remove_assignees:
                obj.assignments.filter(user__in=remove_assignees).delete()

            logger.debug('#{}: [{}] {}'.format(task_id, obj.state, obj.name))

        syncher.finish()

    def sync_workspaces(self, origin_id=None):
        raise NotImplementedError()

    def sync_tasks(self, workspace):
        """
        Read tasks for a given workspace.
        """
        raise NotImplementedError()

    def sync_single_task(self, workspace, task_origin_id):
        """
        Read a single task for a given workspace.
        """
        raise NotImplementedError()

    def save_users(self, users):
        def mark_inactive(dsu):
            # Currently we don't mark DataSourceUsers inactive
            return

        DataSourceUser = self.data_source.data_source_users.model
        syncher = ModelSyncher(self.data_source.data_source_users.all(),
                               lambda dsu: dsu.origin_id,
                               delete_func=mark_inactive, delete_limit=None)
        for user in users:
            obj = syncher.get(user['origin_id'])
            if not obj:
                obj = DataSourceUser(data_source=self.data_source)
            for attr_name, value in user.items():
                setattr(obj, attr_name, value)
            if not obj.id:
                logger.debug('Creating new data source user: %s' % obj)
            obj.save()
            syncher.mark(obj)

        syncher.finish()
