# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):
    account_number = models.CharField(max_length=255, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'account'

    def __unicode__(self):
        return "%s" % self.account_number


class Transaction(models.Model):
    transaction_reference = models.CharField(max_length=160)
    transaction_category = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entry_type = models.CharField(max_length=64, null=True, blank=True)
    account = models.ForeignKey(Account, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    provider_reference = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, related_name="transaction_user")
    created_by_name = models.CharField(max_length=160, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transaction'

    def __unicode__(self):
        return "%s" % self.transaction_reference


