# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-05-04 10:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_transaction_balance_after'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='provider_reference',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]