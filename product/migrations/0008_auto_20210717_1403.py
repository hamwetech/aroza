# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-07-17 11:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0007_auto_20210717_0937'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Retail Price'),
        ),
    ]
