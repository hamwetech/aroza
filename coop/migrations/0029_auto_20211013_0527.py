# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-10-13 02:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coop', '0028_auto_20211008_1037'),
    ]

    operations = [
        migrations.AddField(
            model_name='cooperative',
            name='external_data_token',
            field=models.CharField(default=b'', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cooperative',
            name='external_data_url',
            field=models.CharField(default=b'', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cooperative',
            name='get_external_data',
            field=models.BooleanField(default=False),
        ),
    ]
