# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-05-04 05:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coop', '0032_auto_20220422_0538'),
    ]

    operations = [
        migrations.AddField(
            model_name='cooperativemember',
            name='ensuubuko_customer_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
