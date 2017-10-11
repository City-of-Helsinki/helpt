import pytest
from users.models import Organization, User


@pytest.mark.django_db
def test_organization_api_list(api_client, org_list_url, org):
    response = api_client.get(org_list_url)
    assert response.status_code == 200
    org_list = response.data['organization']
    assert len(org_list) == 1
    assert org_list[0]['name'] == 'org1'


@pytest.mark.django_db
def test_organization_api_autosuggest(api_client, org_list_url, org):
    org2 = Organization.objects.create(name='Zaphod')
    org3 = Organization.objects.create(name='Zaphid')
    org_ids = set([org2.id, org3.id])

    response = api_client.get(org_list_url, data=dict(autosuggest='z'))
    assert response.status_code == 200
    org_list = response.data['organization']
    assert len(org_list) == 2
    assert set([x['id'] for x in org_list]) == org_ids

    response = api_client.get(org_list_url, data=dict(autosuggest='zapho'))
    assert response.status_code == 200
    org_list = response.data['organization']
    assert len(org_list) == 1
    assert org_list[0]['id'] == org2.id


@pytest.mark.django_db
def test_user_api_list(api_client, user_list_url, user):
    response = api_client.get(user_list_url)
    assert response.status_code == 200
    user_list = response.data['user']
    assert len(user_list) == 1
    assert user_list[0]['username'] == 'test_user'


@pytest.mark.django_db
def test_user_api_autosuggest(api_client, user_list_url, user):
    user_dict = dict(first_name='Jack', last_name='Daniels', username='jackd', email='jack.daniels@example.com')
    user2 = User.objects.create(**user_dict)
    user_dict.update(dict(first_name='Jill'), username='jilld', email='jill.daniels@example.com')
    user3 = User.objects.create(**user_dict)
    user_ids = set([str(user2.uuid), str(user3.uuid)])

    response = api_client.get(user_list_url, data=dict(autosuggest='j'))
    assert response.status_code == 200
    obj_list = response.data['user']
    assert len(obj_list) == 2
    assert set([x['id'] for x in obj_list]) == user_ids

    response = api_client.get(user_list_url, data=dict(autosuggest='ja'))
    assert response.status_code == 200
    obj_list = response.data['user']
    assert len(obj_list) == 1
    assert obj_list[0]['id'] == str(user2.uuid)
