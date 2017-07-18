import pytest
from workspaces.tests.conftest import (  # noqa
    api_client, user_api_client, task, data_source_user, workspace, data_source, user, data_source_user,
    task_assignment, user2
)
from hours.models import Entry


@pytest.fixture
@pytest.mark.django_db
def entry(task_assignment):
    return Entry.objects.create(
        user=task_assignment.user.user, date='2100-01-01', task=task_assignment.task, minutes=30
    )
