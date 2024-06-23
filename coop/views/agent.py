# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import xlrd
import datetime
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.encoding import smart_str
from django.db import transaction
from django.db.models import Count, Q
from django.views.generic import View, ListView, FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from conf.utils import log_debug, log_error, get_deleted_objects, get_consontant_upper
from conf.models import District, County, SubCounty
from coop.models import *
from coop.forms import *
from userprofile.models import Profile, AccessLevel


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context


class AgentListView(ExtraContext, ListView):
    template_name = 'coop/agents_list.html'

    def get(self, request, **kwargs):

        name = self.request.GET.get('name')
        phone_number = self.request.GET.get('phone_number')
        cooperative = self.request.GET.get('cooperative')
        end_date = self.request.GET.get('end_date')
        start_date = self.request.GET.get('start_date')

        agents = Agent.objects.all()

        if not request.user.profile.is_union():
            cooperative = request.user.cooperative_admin.cooperative
            agents = agents.filter(user__cooperative_admin__cooperative=cooperative)

        if phone_number:
            agents = agents.filter(phone_number=phone_number)

        if name:
            agents = agents.filter(Q(user__first_name__icontains=name) | Q(user__last_name__icontains=name))

        agent_summary = []
        for a in agents:
            queryset = CooperativeMember.objects.filter(create_by=a.user)

            if start_date:
                queryset = queryset.filter(create_date__gte=start_date)

            if end_date:
                queryset = queryset.filter(create_date__lte=end_date)

            if cooperative:
                queryset = queryset.filter(cooperative_id=cooperative)
            agent_summary.append({'agent': a, 'members': queryset.count()})


        data = {
            'agent_summary': agent_summary,
            'form': AgentSearchForm(request.GET),
            'active': ['_agent']
        }
        return render(request, self.template_name, data)


class AgentCreateFormView(ExtraContext, FormView):
    template_name = "coop/agent_form.html"
    form_class = AgentForm
    extra_context = {'active': ['_agent']}
    success_url = reverse_lazy('coop:agent_list')

    def form_valid(self, form):
        # f = super(SupplierUserCreateView, self).form_valid(form)
        instance = None
        try:
            while transaction.atomic():
                self.object = form.save()
                if not instance:
                    self.object.set_password(form.cleaned_data.get('password'))
                self.object.save()

                profile = self.object.profile

                profile.msisdn=form.cleaned_data.get('msisdn')
              
                profile.access_level=get_object_or_404(AccessLevel, name="AGENT")
                profile.save()

                coops = form.cleaned_data.get('cooperative')
                
                for coop in coops:
                    print(coop)
                    CooperativeAdmin.objects.create(
                        user=self.object,
                        cooperative = get_object_or_404(Cooperative, pk=coop),
                        created_by =self.request.user
                    )
                return super(AgentCreateFormView, self).form_valid(form)
        except Exception as e:
            form.add_error(None, 'Error: %s.' % e)
            return super(AgentCreateFormView, self).form_invalid(form)