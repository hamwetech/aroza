# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from activity.models import *
from activity.forms import *

from conf.utils import generate_alpanumeric, log_debug, log_error

class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context['active'] = ['_training']
        context['title'] = 'Training'
        context.update(self.extra_context)
        return context

class ThematicAreaCreateView(ExtraContext, CreateView):
    model = ThematicArea
    form_class = ThematicAreaForm
    extra_context = {'active': ['_training', '__thematic']}
    success_url = reverse_lazy('activity:thematic_list')
    
    
class ThematicAreaUpdateView(ExtraContext, UpdateView):
    model = ThematicArea
    form_class = ThematicAreaForm
    extra_context = {'active': ['_training', '__thematic']}
    success_url = reverse_lazy('activity:thematic_list')
    
    
class ThematicAreaListView(ExtraContext, ListView):
    model = ThematicArea
    extra_context = {'active': ['_training', '__thematic']}
    

class TrainingSessionListView(ExtraContext, ListView):
    model = TrainingSession
    extra_context = {'active': ['_training', '__training']}
    ordering = ['-training_start']
    
    def get_queryset(self):
        queryset = super(TrainingSessionListView, self).get_queryset()
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            queryset = queryset.filter(trainer__cooperative_admin__cooperative=cooperative)
        return queryset
    
class TrainingSessionDetailView(ExtraContext, DetailView):
    model = TrainingSession
    extra_context = {'active': ['_training', '__training']}
    

class TrainingCreateView(ExtraContext, CreateView):
    model = TrainingSession
    form_class = TrainingForm
    extra_context = {'active': ['_training', '__training']}
    success_url = reverse_lazy('activity:training_list')
    
    def form_valid(self, form):
        form.instance.training_reference = generate_alpanumeric(prefix="TR", size=8)
        form.instance.created_by = self.request.user
        training = super(TrainingCreateView, self).form_valid(form)
        return training
    
    
class ExternalTrainerCreateView(CreateView):
    model = ExternalTrainer
    form_class = ExternaTrainerForm
    extra_context = {'active': ['_training', '__training']}
    success_url = reverse_lazy('activity:training_create')


class TrainingContentCreateView(CreateView):
    model = TrainingContent
    form_class = TrainingContentForm

    def form_valid(self, form):
        pk = self.kwargs.get('thematic')
        thematic = get_object_or_404(ThematicArea, pk=pk)
        form.instance.thematic_area = thematic
        form.instance.created_by = self.request.user
        return super(TrainingContentCreateView, self).form_valid(form)
        
    def get_success_url(self):
        pk = self.kwargs.get('thematic')
        return reverse_lazy('activity:training_content_list',  kwargs = {'thematic': pk})


class TrainingContentUpdateView(UpdateView):
    model = TrainingContent
    form_class = TrainingContentForm

    def form_valid(self, form):
        pk = self.kwargs.get('thematic')
        thematic = get_object_or_404(ThematicArea, pk=pk)
        form.instance.thematic_area = thematic
        form.instance.created_by = self.request.user
        return super(TrainingContentUpdateView, self).form_valid(form)

    def get_success_url(self):
        pk = self.kwargs.get('thematic')
        return reverse_lazy('activity:training_content_list', kwargs={'thematic': pk})


class TrainingContentListView(ListView):
    model = TrainingContent
    extra_context = {'active': ['_training', '__training']}

    def get_queryset(self):
        queryset = super(TrainingContentListView, self).get_queryset()
        thematic = self.kwargs.get('thematic')
        queryset = queryset.filter(thematic_area=thematic)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(TrainingContentListView, self).get_context_data(**kwargs)
        pk = self.kwargs.get('thematic')
        print(pk)
        context['thematic_area']  = ThematicArea.objects.get(pk=pk)
        return context


    
