# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-10-12 19:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0012_trainingcontent_sequence'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingcontent',
            name='thematic_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='activity.ThematicArea'),
        ),
    ]
