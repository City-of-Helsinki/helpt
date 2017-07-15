from django.core.urlresolvers import reverse
from django.core.management.base import BaseCommand
from workspaces.models import DataSource
from workspaces.adapters.trello import receive_trello_hook


class Command(BaseCommand):
    help = "Install webhook handlers for Trello boards"

    def add_arguments(self, parser):
        parser.add_argument('base-url', nargs=1,
                            help="Base URL for the webhook handler")

    def handle(self, *args, **options):
        ds_list = DataSource.objects.filter(type='trello', workspaces__sync=True).distinct()
        if not ds_list:
            self.stdout.write(self.style.WARNING("No Trello data sources with sync-enabled workspaces"))
            return
        base_url = options.get('base-url')[0].rstrip('/')
        handler_url = base_url + reverse(receive_trello_hook)
        self.stdout.write("Registering webhooks for handler: %s" % handler_url)
        for ds in ds_list:
            for ws in ds.workspaces.filter(sync=True):
                self.stdout.write("Registering webhook for workspace %s: " % ws, ending='')
                ds.adapter.register_workspace_webhook(ws, handler_url)
                self.stdout.write(self.style.SUCCESS("success"))
