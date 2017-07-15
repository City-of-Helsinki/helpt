from django.core.management.base import BaseCommand
from workspaces.models import DataSource


class Command(BaseCommand):
    help = "Clear webhook handlers for Trello boards"

    def handle(self, *args, **options):
        ds_list = DataSource.objects.filter(type='trello', workspaces__sync=True).distinct()
        if not ds_list:
            self.stdout.write(self.style.WARNING("No Trello data sources with sync-enabled workspaces"))
            return
        for ds in ds_list:
            self.stdout.write("Clearing webhooks for %s" % ds)
            ds.adapter.clear_webhooks()
