from dynamic_rest import serializers, viewsets
from .models import Task, Workspace, Project, DataSource
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


class ProjectSerializer(serializers.DynamicModelSerializer):
    class Meta:
        model = Project
        name = 'project'
        plural_name = 'project'


@register_view
class ProjectViewSet(viewsets.DynamicModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class DataSourceSerializer(serializers.DynamicModelSerializer):
    class Meta:
        model = DataSource
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
        name = 'workspace'
        plural_name = 'workspace'


@register_view
class WorkspaceViewSet(viewsets.DynamicModelViewSet):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer


class TaskSerializer(serializers.DynamicModelSerializer):
    workspace = serializers.DynamicRelationField(WorkspaceSerializer)
    assigned_users = serializers.DynamicRelationField(UserSerializer, many=True)

    class Meta:
        model = Task
        name = 'task'
        plural_name = 'task'

@register_view
class TaskViewSet(viewsets.DynamicModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def list(self, request, *args, **kwargs):
        # Modify user filter to apply to nested relation
        userfilter = request.query_params.get('filter{assigned_users}')
        if userfilter:
            del(request.query_params['filter{assigned_users}'])
            request.query_params.add('filter{assigned_users.user}', userfilter)

        return super(TaskViewSet, self).list(request, *args, **kwargs)
