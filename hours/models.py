from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError


class Entry(models.Model):
    STATES = (
        ('public', 'public'),
        ('deleted', 'deleted'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True,
                             related_name='entries', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    task = models.ForeignKey('workspaces.Task', db_index=True, related_name='entries',
                             on_delete=models.CASCADE)
    minutes = models.PositiveIntegerField()

    state = models.CharField(max_length=20, choices=STATES, default='public')

    class Meta:
        ordering = ('-date',)
        unique_together = (('user', 'task', 'date'),)

    def clean(self):
        qs = Entry.objects.filter(user=self.user, task=self.task, date=self.date)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(_("There is an hour entry already for this (user, task, date) combination"))
        return super().clean()

    def __str__(self):
        return "{}: {:2f}h on {} by {}".format(self.date, self.minutes / 60.0,
                                               self.task, self.user)
