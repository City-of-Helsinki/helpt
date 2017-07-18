import pytest
from django.core.urlresolvers import reverse

from hours.models import Entry


ENTRY_LIST_URL = reverse('v1:entry-list')


def get_entry_detail_url(entry):
    return reverse('v1:entry-detail', kwargs={'pk': entry.pk})


@pytest.fixture
def new_entry_data(task_assignment):
    data = dict(user=task_assignment.user.user.uuid, task=task_assignment.task.pk,
                minutes=30, date='2100-01-01')
    return data


@pytest.mark.django_db
def test_api_create_entry(user_api_client, new_entry_data):
    assert Entry.objects.count() == 0
    response = user_api_client.post(ENTRY_LIST_URL, data=new_entry_data, format='json')
    assert response.status_code == 201
    assert Entry.objects.count() == 1

    # Posting a duplicate should return a validation error
    response = user_api_client.post(ENTRY_LIST_URL, data=new_entry_data, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_api_update_entry(user_api_client, user2, entry):
    detail_url = get_entry_detail_url(entry)
    response = user_api_client.get(detail_url, format='json')
    assert response.status_code == 200
    data = response.json()['entry']

    response = user_api_client.put(detail_url, data, format='json')
    assert response.status_code == 200

    data['minutes'] += 30
    response = user_api_client.put(detail_url, data, format='json')
    assert response.status_code == 200
    assert Entry.objects.count() == 1
    entry = Entry.objects.first()
    assert entry.minutes == data['minutes']

    user_api_client.force_authenticate(user=user2)
    response = user_api_client.put(detail_url, data, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_api_create_entry_anonymous(api_client, new_entry_data):
    response = api_client.post(ENTRY_LIST_URL, data=new_entry_data, format='json')
    assert response.status_code == 401
