# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import transaction
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import View, ListView
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.models import User

from conf.utils import log_error, log_debug
from userprofile.models import Profile
from userprofile.forms import UserProfileForm, UserForm, CooperativeAdminForm
from coop.models import OtherCooperativeAdmin, Cooperative, CooperativeAdmin


# class UserProfileCreateView(CreateView):
#     model = Profile
#     form_class = UserProfileForm
#     success_url = reverse_lazy('profile:user_list')


class UserProfileCreateView(View):
    template_name = "userprofile/profile_form.html"

    def get(self, request, *arg, **kwarg):
        pk = self.kwargs.get('pk')
        instance = None
        profile = None
        coop_admin = None
        initial = None
        if pk:
            user = User.objects.get(pk=pk)
            if user:
                instance = user
                other = OtherCooperativeAdmin.objects.values_list('cooperative__id', flat=True).filter(user=instance)
                print(other)
                initial = {"other_cooperative": [x for x in other]}
                profile = instance.profile
                if hasattr(instance, 'cooperative_admin'):
                    coop_admin = instance.cooperative_admin

        user_form = UserForm(instance=instance)
        profile_form = UserProfileForm(instance=profile, initial=initial, request=self.request)

        coop_form = CooperativeAdminForm(instance=coop_admin, request=self.request)
        data = {'user_form': user_form, 'profile_form': profile_form, 'coop_form': coop_form}
        return render(request, self.template_name, data)

    def post(self, request, *arg, **kwargs):
        pk = self.kwargs.get('pk')
        instance = None
        profile = None
        coop_admin = None
        errors = dict()

        if pk:
            instance = User.objects.filter(pk=pk)
            if instance.exists():
                instance = instance[0]
                profile = instance.profile
                if hasattr(instance, 'cooperative_admin'):
                    coop_admin = instance.cooperative_admin
        user_form = UserForm(request.POST, instance=instance)
        profile_form = UserProfileForm(request.POST, instance=profile, request=self.request)
        coop_form = CooperativeAdminForm(request.POST, instance=coop_admin, request=self.request)

        if user_form.is_valid() and profile_form.is_valid() and coop_form.is_valid():
            try:
                with transaction.atomic():

                    if profile_form.cleaned_data.get('access_level'):
                        if coop_form.cleaned_data.get('cooperative'):
                            print(profile_form.cleaned_data.get('access_level').name.lower() == 'cooperative' or profile_form.cleaned_data.get('access_level').name.lower() == 'agent')
                            if profile_form.cleaned_data.get('access_level').name.lower() == 'cooperative' or profile_form.cleaned_data.get('access_level').name.lower() == 'agent':
                                pass
                            else:
                                errors['errors'] = "Only Cooperate Level Users can be assigned to a Cooperative"

                    if not errors:
                        user = user_form.save(commit=False);
                        if not instance:
                            user.set_password(user.password)
                        user.save()
                        profile_form = UserProfileForm(request.POST, instance=user.profile, request=self.request)
                        profile_form.save()

                        if coop_form.cleaned_data.get('cooperative'):
                            c = coop_form.save(commit=False)
                            c.user = user
                            c.save()

                        if profile_form.cleaned_data.get('other_cooperative'):
                            OtherCooperativeAdmin.objects.filter(user=user).delete()
                            for c in profile_form.cleaned_data.get('other_cooperative'):
                                OtherCooperativeAdmin.objects.create(
                                    user=user,
                                    cooperative=Cooperative.objects.get(pk=c),
                                )
                        return redirect('profile:user_list')
            except Exception as e:
                log_error()
                errors['errors'] = "Error %s" % e
        data = {'user_form': user_form, 'profile_form': profile_form, 'coop_form': coop_form}
        data.update(errors)
        return render(request, self.template_name, data)


class UserProfileUpdateView(UpdateView):
    model = Profile
    form_class = UserProfileForm
    success_url = reverse_lazy('profile:user_list')


class UserProfileListView(ListView):
    model = Profile

    def get_queryset(self):
        queryset = super(UserProfileListView, self).get_queryset()
        u = []
        if hasattr(self.request.user, 'cooperative_admin'):
            [u.append(x.user) for x in CooperativeAdmin.objects.filter(cooperative=self.request.user.cooperative_admin.cooperative)]
            print(u)
            queryset = queryset.filter(user__in=u)
        return queryset
