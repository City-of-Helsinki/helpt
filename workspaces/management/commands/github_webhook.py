from django.core.urlresolvers import reverse
from django.core.management.base import BaseCommand
from workspaces.models import GitHubDataSource, DataSourceWebhook
from workspaces.adapters.github import receive_github_hook


class Command(BaseCommand):
    help = "Install and remove webhook handlers for GitHub organizations"

    def add_arguments(self, parser):
        parser.add_argument('-c', '--clear', dest='clear', action='store_true',
                            help="Remove configured webhooks")
        parser.add_argument('-a', '--add', dest='add', metavar='BASE_URL', action='store',
                            help="Add a new webhook")

    def handle(self, *args, **options):
        if options['clear']:
            hooks = DataSourceWebhook.objects.filter(data_source__type='github')
            for hook in hooks:
                ds = hook.data_source
                ds.adapter.remove_webhook(hook.origin_id)

        if options['add']:
            ds_list = GitHubDataSource.objects.filter(workspaces__sync=True).distinct()
            if not ds_list:
                self.stdout.write(self.style.WARNING("No GitHub data sources with sync-enabled workspaces"))
                return
            base_url = options.get('add').rstrip('/')
            handler_url = base_url + reverse(receive_github_hook)
            self.stdout.write("Registering webhooks for handler: %s" % handler_url)
            for ds in ds_list:
                self.stdout.write("Registering webhook for data source %s: " % ds, ending='')
                ds.adapter.register_webhook(handler_url)
                self.stdout.write(self.style.SUCCESS("success"))
