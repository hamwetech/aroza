# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-07-15 17:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coop', '0019_auto_20210715_1517'),
        ('credit', '0003_auto_20210715_2005'),
    ]

    operations = [
        migrations.AddField(
            model_name='loanrequest',
            name='order_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='coop.OrderItem'),
        ),
    ]
