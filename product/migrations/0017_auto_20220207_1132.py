# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-02-07 08:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0016_auto_20210731_2226'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='item',
            name='supplier_item_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
