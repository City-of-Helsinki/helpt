# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-11 19:01
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0009_add_project_field_to_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='extra_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]