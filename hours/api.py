from django.core.exceptions import (
    PermissionDenied, ValidationError as DjangoValidationError
)
from dynamic_rest import serializers, viewsets, fields
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from .models import Entry
from users.api import UserSerializer
from workspaces.api import TaskSerializer


all_views = []


def register_view(klass, name=None, base_name=None):
    if not name:
        name = klass.serializer_class.Meta.name

    entry = {'class': klass, 'name': name}
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)

    return klass


class UUIDBasedRelationField(fields.DynamicRelationField):
    def to_internal_value_single(self, data, serializer):
        related_model = serializer.Meta.model
        if isinstance(data, related_model):
            return data
        try:
            instance = related_model.objects.get(uuid=data)
        except related_model.DoesNotExist:
            raise fields.NotFound(
                "'%s object with ID=%s not found" %
                (related_model.__name__, data)
            )
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if not isinstance(ret, int):
            return ret
        related_model = self.serializer.get_model()
        return related_model.objects.get(id=ret).uuid


class EntryPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user.is_authenticated():
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if obj.user == request.user:
            return True

        return False


class EntrySerializer(serializers.DynamicModelSerializer):
    user = UUIDBasedRelationField(UserSerializer)
    task = serializers.DynamicRelationField(TaskSerializer)

    class Meta:
        model = Entry
        fields = ['id', 'user', 'date', 'task', 'minutes', 'state']
        name = 'entry'
        plural_name = 'entry'

    def validate(self, data):
        data = super().validate(data)
        entry = Entry(**data)
        if self.instance:
            entry.pk = self.instance.pk
        try:
            entry.clean()
        except DjangoValidationError as exc:
            if not hasattr(exc, 'error_dict'):
                raise ValidationError(exc)
            error_dict = {}
            for key, value in exc.error_dict.items():
                error_dict[key] = [error.message for error in value]
            raise ValidationError(error_dict)

        return data


class EntryViewSet(viewsets.DynamicModelViewSet):
    queryset = Entry.objects.all()
    serializer_class = EntrySerializer
    permission_classes = (EntryPermission,)

    def create(self, *args, **kwargs):
        return super().create(*args, **kwargs)

    def update(self, *args, **kwargs):
        return super().update(*args, **kwargs)

register_view(EntryViewSet, name='entry')
