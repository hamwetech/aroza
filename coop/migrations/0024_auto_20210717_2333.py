# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-07-17 20:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coop', '0023_cooperativemember_account'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cooperativemember',
            name='account',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='account.Account'),
        ),
    ]