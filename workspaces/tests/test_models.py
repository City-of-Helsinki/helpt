import pytest
from workspaces.models import Task


@pytest.mark.django_db
def test_create_task(task):
    assert Task.objects.count() == 1
