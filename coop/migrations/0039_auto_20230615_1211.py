# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2023-06-15 09:11
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0017_auto_20220207_1132'),
        ('conf', '0002_systemsettings_mobile_money_payment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('coop', '0038_cooperative_saving_product'),
    ]

    operations = [
        migrations.CreateModel(
            name='FarmerGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('code', models.CharField(blank=True, max_length=150, null=True, unique=True)),
                ('village', models.CharField(blank=True, max_length=255, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=12, null=True)),
                ('contact_person_name', models.CharField(max_length=150)),
                ('contact_person_number', models.CharField(max_length=150)),
                ('contribution_total', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('shares', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('is_active', models.BooleanField(default=0)),
                ('send_message', models.BooleanField(default=0, help_text="If not set, the cooperative member will not receive SMS's when sent.")),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('cooperative', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='coop.Cooperative')),
                ('county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='conf.County')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('district', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='conf.District')),
                ('parish', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='conf.Parish')),
                ('product', models.ManyToManyField(blank=True, to='product.Product')),
                ('sub_county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='conf.SubCounty')),
            ],
            options={
                'db_table': 'farmer_group',
            },
        ),
        migrations.AddField(
            model_name='cooperativemember',
            name='farmer_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='coop.FarmerGroup'),
        ),
    ]
