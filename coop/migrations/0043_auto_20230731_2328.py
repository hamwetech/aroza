# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2023-07-31 20:28
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('coop', '0042_auto_20230731_1845'),
    ]

    operations = [
        migrations.AddField(
            model_name='cooperativemember',
            name='has_insurance',
            field=models.BooleanField(default=0),
        ),
        migrations.AddField(
            model_name='okomemberpolicy',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]