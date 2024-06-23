# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.generic import View, ListView, RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm

from conf.utils import log_error, log_debug
from userprofile.models import *
from userprofile.forms import GroupForm, AccessLevelForm, AccessLevelGroupForm, LoginForm
from coop.models import Cooperative
from coop.utils import check_coop_url


class GroupCreateView(CreateView):
    model = Group
    # template_name = "conf/group_form.html"
    form_class = GroupForm
    success_url = reverse_lazy('profile:group_list')


class GroupUpdateView(UpdateView):
    model = Group
    # template_name = "conf/group_form.html"
    form_class = GroupForm
    success_url = reverse_lazy('conf:group_list')


class GroupListView(ListView):
    model = Group


class AccessLevelListView(ListView):
    model = AccessLevel


class AccessLevelCreateView(CreateView):
    model = AccessLevel
    form_class = AccessLevelForm
    success_url = reverse_lazy('profile:access_list')


class AccessLevelUpdateView(UpdateView):
    model = AccessLevel
    form_class = AccessLevelForm
    success_url = reverse_lazy('profile:access_list')


class AccessLevelGroupListView(ListView):
    model = AccessLevelGroup


class AccessLevelGroupCreateView(CreateView):
    model = AccessLevelGroup
    form_class = AccessLevelGroupForm
    success_url = reverse_lazy('profile:ag_list')


class AccessLevelGroupUpdateView(UpdateView):
    model = AccessLevelGroup
    form_class = AccessLevelGroupForm
    success_url = reverse_lazy('profile:ag_list')


class ChangePasswordView(View):
    template_name = 'userprofile/change_password.html'

    def get(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            password = form.cleaned_data.get('new_password2')
            check = password_log(request.user, password)
            if check:
                user = form.save()
                data = {
                    'title': 'Password Change',
                    'status_message': 'Your Password has been updated successfully.'
                }
                messages.success(request, 'Password Updated successfully')
                return render(request, 'account/status.html', data)
            messages.error(request,
                           'Sorry password Denied. Please use a password different from your previous %s passwords' % system_settings.password_reuse_threshold)
        return render(request, self.template_name, {'form': form})


class AdminChangePasswordView(View):
    template_name = 'userprofile/change_password.html'

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        user = User.objects.get(pk=pk)
        form = SetPasswordForm(user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        __user = User.objects.get(pk=pk)
        form = SetPasswordForm(__user, request.POST)

        if form.is_valid():
            user = form.save()
            data = {
                'title': 'Password Change',
                'status_message': 'Your Password has been updated successfully.'
            }
            messages.success(request, 'Password Updated successfully')
            return redirect('profile:user_list')
            # messages.success(request, 'Password Updated successfully')
            # return render(request, 'account/status.html', data)
            # return redirect('profile:user_list')
            # messages.error(request, 'Sorry password Denied. Please use a password different from your previous %s passwords' % system_settings.password_reuse_threshold)
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    template_name = "userprofile/login.html"

    def get(self, request, *args, **kwargs):
        data = dict()
        data["form"] = LoginForm
        host = request.get_host()
        log_debug("Host: %s" % host)
        coop = check_coop_url(host)
        log_debug("Cooperative Host: %s" % coop)
        if coop:
            data["coop"] = coop
        return render(request, self.template_name, data)

    def post(self, request, *args, **kwargs):
        data = dict()
        form = LoginForm(request.POST)
        cooperative = False
        right_cooperative = None
        host = request.get_host()
        coop = check_coop_url(host)
        if coop:
            data["coop"] = coop
        try:

            if form.is_valid():
                # set_login_attempt(request)
                username = form.cleaned_data.get('username', '')
                password = form.cleaned_data.get('password', '')

                user = authenticate(username=username, password=password)
                if user:
                    if user.is_active:

                        if user.profile.access_level or user.is_superuser:

                            if hasattr(user.profile.access_level, 'name'):
                                if user.profile.access_level.name.lower() == "cooperative" and user.cooperative_admin:
                                    cooperative = True
                                if coop:
                                    right_cooperative = "False"
                                    if coop == user.cooperative_admin.cooperative:
                                        right_cooperative = "True"
                            if cooperative or user.profile.is_union() or user.profile.is_partner() or user.profile.is_supplier() or user.profile.is_credit_manager():
                                print(right_cooperative)
                                print(cooperative)
                                if cooperative:
                                    if not right_cooperative:
                                        login(request, user)
                                        return redirect('dashboard')
                                    if right_cooperative == "True":
                                        login(request, user)
                                        return redirect('dashboard')
                                    if right_cooperative == "False":
                                        data['errors'] = "Cooperative not identified. Please contact the Admin"
                                elif user.profile.is_union() or user.profile.is_supplier() or user.profile.is_partner() or user.is_superuser or user.profile.is_credit_manager():
                                    if not coop:
                                        login(request, user)
                                        return redirect('dashboard')
                                    else:
                                        data['errors'] = "Cooperative Access Denied. Please contact the Admin"
                                else:
                                    data['errors'] = "Your Cooperative Credentials Failed. Please try again"
                            else:
                                data['errors'] = "Your Cooperative not identified. Please contact the Admin"
                        else:
                            data['errors'] = "You do not permission to Signin. Please contact the Admin"
                    else:
                        data['errors'] = "Your account is inactive"
                else:
                    data['errors'] = "Username or Password invalid"

        except Exception:
            data['errors'] = "Login Error. Contact Admin"
            log_error()
        data['form'] = form
        return render(request, self.template_name, data)


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')
        # return super(LogoutView, self).get(request, *args, **kwargs)

