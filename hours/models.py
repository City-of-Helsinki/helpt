from django.conf import settings
from django.db import models


class Entry(models.Model):
    STATES = (
        ('public', 'public'),
        ('deleted', 'deleted'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True,
                             related_name='entries')
    date = models.DateField(db_index=True)
    task = models.ForeignKey('workspaces.Task', db_index=True, related_name='entries')
    minutes = models.PositiveIntegerField()

    state = models.CharField(max_length=20, choices=STATES, default='public')

    def __str__(self):
        return "{}: {:2f}h on {} by {}".format(self.date, self.minutes / 60.0,
                                               self.task, self.user)
