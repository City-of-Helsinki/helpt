import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from workspaces.models import (
    DataSource, DataSourceUser, Workspace, Task, TaskAssignment
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
@pytest.fixture
def user():
    return get_user_model().objects.create(
        username='test_user',
        first_name='Cem',
        last_name='Kaner',
        email='cem@kaner.com',
    )


@pytest.mark.django_db
@pytest.fixture
def user2():
    return get_user_model().objects.create(
        username='test_user2',
        first_name='Brendan',
        last_name='Neutra',
        email='brendan@neutra.com'
    )


@pytest.mark.django_db
@pytest.fixture
def data_source():
    return DataSource.objects.create(type='test', name="Test Datasource")


@pytest.mark.django_db
@pytest.fixture
def workspace(data_source):
    return Workspace.objects.create(
        data_source=data_source, name="Test workspace", origin_id='ws1'
    )


@pytest.mark.django_db
@pytest.fixture
def data_source_user(data_source, user):
    return DataSourceUser.objects.create(
        data_source=data_source, user=user, origin_id='dsu1'
    )


@pytest.mark.django_db
@pytest.fixture
def task(workspace):
    return Task.objects.create(
        workspace=workspace, origin_id='task1', state='open'
    )


@pytest.mark.django_db
@pytest.fixture
def task_assignment(task, data_source_user):
    return TaskAssignment.objects.create(task=task, user=data_source_user)
