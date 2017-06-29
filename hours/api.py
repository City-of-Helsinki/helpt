from dynamic_rest import serializers, viewsets, fields
from .models import Entry
from users.api import UserSerializer


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


class EntrySerializer(serializers.DynamicModelSerializer):
    user = UUIDBasedRelationField(UserSerializer)

    class Meta:
        model = Entry
        fields = ['id', 'user', 'date', 'task', 'minutes', 'state']
        name = 'entry'
        plural_name = 'entry'


@register_view
class EntryViewSet(viewsets.DynamicModelViewSet):
    queryset = Entry.objects.all()
    serializer_class = EntrySerializer
