# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-02-20 18:52
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0002_auto_20190220_2151'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trainingsession',
            name='training_module',
        ),
    ]