from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf.urls import url
import json

from ..models import Workspace

@csrf_exempt
@require_POST
def receive_github_hook(request):
    # TODO: Verify IP whitelist
    # TODO: Verify shared secret
    try:
        event_type = request.META['HTTP_X_GITHUB_EVENT']
    except KeyError:
        return HttpResponseBadRequest("GitHub event type missing")

    # Respond to GitHub ping event, not really necessary, but cute
    if event_type == "ping":
        return HttpResponse("pong")

    if event_type != "issues":
        return HttpResponseBadRequest("Event type is not \"issues\". Bad hook configuration?")

    try:
        event = json.loads(request.body.decode("utf-8"))
    # What's the exception for invalid utf-8?
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON received")
    except UnicodeError:
        return HttpResponseBadRequest("Invalid character encoding, expecting UTF-8")

    # Task management only cares about GitHub issues
    if 'issue' in event:
        issue_identifier = event['issue']['number']
    else:
        return HttpResponseBadRequest("Issue structure missing. Bad hook configuration?")

    if 'repository' in event:
        event_origin = event['repository']['full_name']
    else:
        return HttpResponseBadRequest("Repository information missing, should be included with issue")

    # Import trauma, possibly related to circular imports
    #Workspace = apps.get_model(app_label='projects', model_name='Workspace')

    try:
        workspace = Workspace.objects.get(origin_id=event_origin)
    except Workspace.DoesNotExist:
        # TODO: Create missing workspaces
        return HttpResponse("processed, no applicable workspaces found")

    # Tasks must be fetched through workspaces, as their identifiers
    # are only unique within workspace
    try:
        task = workspace.tasks.get(origin_id=issue_identifier)
    except Task.DoesNotExist:
        task = Task(workspace=workspace, origin_id=issue_identifier)

    adapter = workspace.data_source.adapter

    users_by_id = adapter._get_users_by_id()

    adapter.update_task(task, event['issue'], users_by_id)

    return HttpResponse("processed, acted on")

urls = [url(r'$^', receive_github_hook)]
