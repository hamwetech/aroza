# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-12-16 10:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credit', '0007_loantransaction_loan'),
    ]

    operations = [
        migrations.AddField(
            model_name='loanrequest',
            name='loan_request_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='loanrequest',
            name='response',
            field=models.TextField(blank=True, null=True),
        ),
    ]
