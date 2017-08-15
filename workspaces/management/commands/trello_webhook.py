from django.core.urlresolvers import reverse
from django.core.management.base import BaseCommand
from workspaces.models import TrelloDataSource, DataSourceWebhook
from workspaces.adapters.trello import receive_trello_hook


class Command(BaseCommand):
    help = "Install and remove webhook handlers for Trello boards"

    def add_arguments(self, parser):
        parser.add_argument('-c', '--clear', dest='clear', action='store_true',
                            help="Remove configured webhooks")
        parser.add_argument('-a', '--add', dest='add', metavar='BASE_URL', action='store',
                            help="Add a new webhook")

    def handle(self, *args, **options):
        ds = TrelloDataSource.objects.filter(workspaces__sync=True).distinct()
        if options['clear']:
            hooks = DataSourceWebhook.objects.filter(data_source__type='trello')
            for hook in hooks:
                ds = hook.data_source
                ds.adapter.remove_webhook(hook.origin_id)

        if options['add']:
            ds_list = TrelloDataSource.objects.filter(workspaces__sync=True).distinct()
            if not ds_list:
                self.stdout.write(self.style.WARNING("No GitHub data sources with sync-enabled workspaces"))
                return
            base_url = options.get('add').rstrip('/')
            handler_url = base_url + reverse(receive_trello_hook)
            self.stdout.write("Registering webhooks for handler: %s" % handler_url)
            for ds in ds_list:
                for ws in ds.workspaces.filter(sync=True):
                    self.stdout.write("Registering webhook for workspace %s: " % ws, ending='')
                    ds.adapter.register_workspace_webhook(ws, handler_url)
                    self.stdout.write(self.style.SUCCESS("success"))
