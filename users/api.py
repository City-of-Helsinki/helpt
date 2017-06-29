from dynamic_rest import serializers, viewsets
from rest_framework import serializers as drf_serializers
from .models import User


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

    class Meta:
        model = User
        name = 'user'
        fields = ['id', 'department_name', 'email', 'first_name', 'last_name', 'username']
        plural_name = 'user'


@register_view
class UserViewSet(viewsets.DynamicModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = super(UserViewSet, self).get_queryset()
        filters = self.request.query_params
        if 'current' in filters:
            queryset = User.objects.filter(pk=self.request.user.pk)
        return queryset
