# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime
from django.urls import reverse_lazy
from coop.models import CooperativeMember
from account.models import Transaction, Account
from account.forms import SavingsCreditForm
from django.views.generic import ListView, DetailView, View, FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from conf.utils import generate_numeric, generate_alpanumeric

from api.Mobis import Mobis


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)

        context.update(self.extra_context)
        return context


class TransactionListview(ExtraContext, ListView):
    model = Transaction
    extra_context = {'active': ['_credit', '__transaction']}
    ordering = ('-id')

    def get_queryset(self):
        queryset = super(TransactionListview, self).get_queryset()

        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative
            queryset = queryset.filter(account__member_account__cooperative=cooperative)

        return queryset


class SavingsCreditCreateForm(ExtraContext, FormView):
    form_class = SavingsCreditForm
    template_name = "account/savings_form.html"
    success_url = reverse_lazy('account:transaction_list')

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        member = form.cleaned_data.get('cooperative_member')
        transaction_method = form.cleaned_data.get('transaction_method')
        phone_number = form.cleaned_data.get('phone_number')
        reference = generate_alpanumeric(size=10)

        cmember = CooperativeMember.objects.get(pk=member)
        savings_id = cmember.ensuubuko_savings_id
        bal = cmember.ensuubuko_savings

        print(cmember.ensuubuko_savings_id)

        trx = Transaction.objects.create(
            transaction_reference=reference,
            transaction_category="SAVINGS",
            amount=amount,
            entry_type="CREDIT",
            description="Savings Credit",
        )

        params = {
            "savings_id": savings_id,
            "amount": amount,
            "receipt_number": reference,
            "transaction_date": datetime.now().strftime("%Y-%m-%d"),
            "transaction_fee": 0,
            "transaction_method": transaction_method.title()
        }
        new_balance = bal + amount
        cmember.ensuubuko_savings = new_balance
        cmember.save()

        mobis = Mobis()
        mobis_response = mobis.credit_savings_account(params)
        print(mobis_response)
        if not mobis_response.get("error"):
            trx.provider_reference = mobis_response.get("id")
            trx.balance_after = new_balance
            trx.save()

        return super(SavingsCreditCreateForm, self).form_valid(form)

