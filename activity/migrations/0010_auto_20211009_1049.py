# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-10-09 07:49
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('activity', '0009_auto_20190322_1930'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingContent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'training_content',
            },
        ),
        migrations.CreateModel(
            name='TrainingTopic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('thematic_area', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='activity.ThematicArea')),
            ],
            options={
                'db_table': 'training_topic',
            },
        ),
        migrations.AddField(
            model_name='trainingcontent',
            name='topic',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='activity.TrainingTopic'),
        ),
    ]
