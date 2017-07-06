from dynamic_rest import serializers, viewsets
from .models import Task, Workspace, Project, DataSource, DataSourceUser
from users.api import UserSerializer
import logging

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


class DataSourceSerializer(serializers.DynamicModelSerializer):
    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'type'
        ]
        name = 'data_source'
        plural_name = 'data_source'


@register_view
class DataSourceViewSet(viewsets.DynamicModelViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer


class WorkspaceSerializer(serializers.DynamicModelSerializer):
    data_source = serializers.DynamicRelationField(DataSourceSerializer)

    class Meta:
        model = Workspace
        fields = [
            'id', 'data_source', 'projects', 'name', 'description', 'origin_id',
            'state'
        ]
        name = 'workspace'
        plural_name = 'workspace'


@register_view
class WorkspaceViewSet(viewsets.DynamicModelViewSet):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer


class AssignedUserSerializer(serializers.DynamicModelSerializer):
    def to_representation(self, instance):
        # We don't want to publish DataSourceUsers through API, only
        # local users. This means that if corresponding local user
        # does not yet exist, this is None
        if not instance.user:
            return None
        else:
            return instance.user.uuid

    class Meta:
        model = DataSourceUser
        fields = []


class TaskSerializer(serializers.DynamicModelSerializer):
    workspace = serializers.DynamicRelationField(WorkspaceSerializer)
    assigned_users = serializers.DynamicRelationField(AssignedUserSerializer, many=True)

    def to_representation(self, instance):
        data = super(TaskSerializer, self).to_representation(instance)

        # Representation will return nulls for users that do not have
        # local counterpart. Filter them out here
        if 'assigned_users' in data:
            data['assigned_users'] = [x for x in data['assigned_users'] if x is not None]

        return data

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'workspace', 'origin_id', 'state', 'created_at', 'updated_at', 'closed_at',
            'assigned_users'
        ]
        name = 'task'
        plural_name = 'task'


@register_view
class TaskViewSet(viewsets.DynamicModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def get_queryset(self, *args, **kwargs):
        queryset = super(TaskViewSet, self).get_queryset(*args, **kwargs)
        args = self.request.query_params
        user_filter = args.get('user')
        if user_filter:
            print("filtering")
            queryset = queryset.filter(assigned_users__user__uuid=user_filter)
        return queryset
