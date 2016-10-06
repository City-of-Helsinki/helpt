import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.conf.urls import url
from .adapters import GitHubAdapter
from .models import GitHubDataSource, Workspace

@csrf_exempt
def receive_github_hook(request):
    # Is this still Djangoish (was in '13)
    if request.method ==  "POST":
        # Verify IP whitelist
        # Verify shared secret

        try:
            event_type = request.META['HTTP_X_GITHUB_EVENT']
        except KeyError:
            # If the request is not wholly read, the containing nginx/uwsgi
            # will return "gateway error" instead of the message below
            request.read()
            return HttpResponseBadRequest("GitHub event type missing")

        # Respond to GitHub ping event, not really necessary, but cute
        if event_type == "ping":
            return HttpResponse("pong")

        try:
            event = json.loads(request.body.decode("utf-8"))
        # What's the exception for invalid utf-8?
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON received")

        event_origin = event['repository']['full_name']

        try:
            workspace = Workspace.objects.get(origin_id=event_origin)
        except Workspace.DoesNotExist:
            return HttpResponse("processed, no applicable workspaces found")

        workspace.accept_this_task(event)

        return HttpResponse("processed, acted on")

    else:
        return HttpResponseBadRequest("Only POST accepted")

class TaskChangeHook:
    urls = [url(r'github/', receive_github_hook)]

def front_page(request):
    return render(request, 'front_page.html')
