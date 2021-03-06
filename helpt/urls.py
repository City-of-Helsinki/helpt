"""helpt URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.core.urlresolvers import reverse
from django.views.generic import RedirectView
from helusers import admin
from rest_framework.routers import DefaultRouter

from workspaces.adapters.github import urls as github_hook_cb_urls
from workspaces.adapters.trello import urls as trello_hook_cb_urls
from workspaces.api import all_views as workspace_views
from users.api import all_views as user_views
from hours.api import all_views as hour_views
from projects.api import all_views as project_views

router = DefaultRouter()

for view in workspace_views:
    router.register(view['name'], view['class'], base_name=view.get('base_name'))
for view in user_views:
    router.register(view['name'], view['class'], base_name=view.get('base_name'))
for view in hour_views:
    router.register(view['name'], view['class'], base_name=view.get('base_name'))
for view in project_views:
    router.register(view['name'], view['class'], base_name=view.get('base_name'))


class RedirectToAPIRootView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('v1:api-root')


urlpatterns = [
    url('^', include('django.contrib.auth.urls')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^v1/', include(router.urls, namespace='v1')),
    url(r'^$', RedirectToAPIRootView.as_view()),
    url(r'^hooks/github/', include(github_hook_cb_urls)),
    url(r'^hooks/trello/', include(trello_hook_cb_urls)),
]
