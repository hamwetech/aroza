# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2023-11-22 15:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conf', '0002_systemsettings_mobile_money_payment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('create_date', models.DateTimeField(auto_now=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'region',
            },
        ),
        migrations.AddField(
            model_name='district',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='conf.Region'),
        ),
    ]
