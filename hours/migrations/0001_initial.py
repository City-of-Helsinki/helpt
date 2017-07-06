# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-29 18:10
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspaces', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('minutes', models.PositiveIntegerField()),
                ('state', models.CharField(choices=[('public', 'public'), ('deleted', 'deleted')], default='public', max_length=20)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='workspaces.Task')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
