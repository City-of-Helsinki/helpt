import logging

from .sync import ModelSyncher


logger = logging.getLogger(__name__)


class Adapter(object):
    def __init__(self, data_source):
        self.data_source = data_source

    def _update_workspaces(self, workspaces):
        """
        Synchronizes workspace database based on supplied data dicts
        """
        def close_workspace(ws):
            logger.debug("Marking workspace %s closed" % ws)
            ws.set_state('closed')
            ws.save(update_fields=['state'])

        workspaces = self.fetch_workspaces()

        # Get access to model through trickery because otherwise
        # there would be a circular import.
        Workspace = self.data_source.workspaces.model
        syncher = ModelSyncher(self.data_source.workspaces.open(),
                               lambda ws: ws.origin_id,
                               delete_func=close_workspace)

        for ws in workspaces:
            obj = syncher.get(ws['origin_id'])
            if not obj:
                obj = Workspace(data_source=self.data_source, origin_id=ws['origin_id'])
            for attr_name, value in ws.items():
                setattr(obj, attr_name, value)
            if not obj.id:
                logger.debug('Creating new workspace: %s' % obj)
            obj.save()
            syncher.mark(obj)

        syncher.finish()

    def _update_tasks(self, workspace, tasks):
        def close_task(task):
            logger.debug("Marking %s closed" % task)
            task.set_state('closed')

        users = self.data_source.data_source_users.all().select_related('user')
        users_by_id = {u.origin_id: u for u in users}

        Task = workspace.tasks.model
        syncher = ModelSyncher(workspace.tasks.open(),
                               lambda task: task.origin_id,
                               delete_func=close_task)
        for task in tasks:
            task = task.copy()
            task_id = task.pop('origin_id')
            obj = syncher.get(task_id)
            if not obj:
                obj = Task(workspace=workspace, origin_id=task_id)

            syncher.mark(obj)
            obj.set_state(task.pop('state'), save=False)

            assigned_users = task.pop('assigned_users')

            for attr_name, value in task.items():
                setattr(obj, attr_name, value)
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

    def sync_workspaces(self):
        raise NotImplementedError()

    def sync_tasks(self, workspace):
        """
        Read tasks for a given workspace.
        """
        raise NotImplementedError()

    def save_users(self, users):
        def mark_inactive(dsu):
            if dsu.state != dsu.ACTIVE:
                return
            if dsu.task_assignments.exists():
                return
            logger.debug("Marking data source user %s inactive" % dsu)
            dsu.set_state(dsu.INACTIVE)

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
