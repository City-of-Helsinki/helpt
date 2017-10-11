import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from users.models import Organization


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org_list_url():
    return reverse('v1:organization-list')


@pytest.fixture
def user_list_url():
    return reverse('v1:user-list')


@pytest.mark.django_db
@pytest.fixture
def org():
    return Organization.objects.create(name='org1')


@pytest.mark.django_db
@pytest.fixture
def user():
    return get_user_model().objects.create(
        username='test_user',
        first_name='Cem',
        last_name='Kaner',
        email='cem@kaner.com',
    )
