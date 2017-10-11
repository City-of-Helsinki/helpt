from dynamic_rest import serializers, viewsets
from rest_framework import serializers as drf_serializers
from django.contrib.auth.models import Group
from django.db.models import Q

from .models import User, Organization


all_views = []


def register_view(klass, name=None, base_name=None):
    if not name:
        name = klass.serializer_class.Meta.name

    entry = {'class': klass, 'name': name}
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)

    return klass


class UserSerializer(serializers.DynamicModelSerializer):
    id = drf_serializers.UUIDField(source='uuid')
    groups = serializers.DynamicRelationField('GroupSerializer', many=True)

    class Meta:
        model = User
        name = 'user'
        fields = ['id', 'department_name', 'email', 'first_name', 'last_name', 'username', 'groups']
        plural_name = 'user'


@register_view
class UserViewSet(viewsets.DynamicModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = super(UserViewSet, self).get_queryset()
        filters = self.request.query_params
        if 'current' in filters:
            queryset = queryset.filter(pk=self.request.user.pk)
        if 'autosuggest' in filters:
            value = filters['autosuggest'].lower()
            query = Q(first_name__istartswith=value) | Q(last_name__istartswith=value) | Q(email__istartswith=value)
            queryset = queryset.filter(query)
        return queryset


class GroupSerializer(serializers.DynamicModelSerializer):
    class Meta:
        model = Group
        name = 'group'
        fields = ['id', 'name']
        plural_name = 'group'


@register_view
class GroupViewSet(viewsets.DynamicModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class OrganizationSerializer(serializers.DynamicModelSerializer):
    class Meta:
        model = Organization
        name = 'organization'
        fields = ['id', 'name']
        plural_name = 'organization'


@register_view
class OrganizationViewSet(viewsets.DynamicModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = self.request.query_params
        if 'autosuggest' in filters:
            queryset = Organization.objects.filter(name__istartswith=filters['autosuggest'].lower())
        return queryset
