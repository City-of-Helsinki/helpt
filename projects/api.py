import logging
from dynamic_rest import serializers, viewsets
from .models import Project

all_views = []

logger = logging.getLogger(__name__)


def register_view(klass, name=None, base_name=None):
    if not name:
        name = klass.serializer_class.Meta.name

    entry = {'class': klass, 'name': name}
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)

    return klass


class ProjectSerializer(serializers.DynamicModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']
        name = 'project'
        plural_name = 'project'


@register_view
class ProjectViewSet(viewsets.DynamicModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
