# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class MobisApiRequest(models.Model):
    request = models.TextField()
    response = models.TextField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
