from __future__ import unicode_literals
import json
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.forms.formsets import formset_factory, BaseFormSet
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.models import User

from coop.models import MemberOrder, CooperativeMember
from coop.forms import OrderItemForm, MemberOrderForm
from coop.views.member import save_transaction
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, log_debug, generate_numeric, float_to_intstring, get_deleted_objects,\
get_message_template as message_template
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from conf.utils import generate_numeric
from coop.models import CooperativeMember
from api.Mobis import Mobis


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("-d", "--cooperative", type=int)

    def handle(self, *args, **kwargs):
        cooperative = kwargs["cooperative"] if kwargs["cooperative"] else None
        member = CooperativeMember.objects.filter(ensuubuko_id__isnull=True)
        if cooperative:
            member = CooperativeMember.objects.filter(ensuubuko_id__isnull=True, cooperative__id=cooperative)
        for m in member:
            params = {
                "branch_id": m.cooperative.trust_network_id,
                "title": "",
                "first_name": m.first_name,
                "surname": m.surname,
                "other_name": None,
                "date_of_birth": m.date_of_birth.strftime("%Y-%m-%d"),
                "gender": m.gender,
                "phone_number": m.phone_number,
                "mobile_money_num": None,
                "parish": m.village ,
                "district": m.district.name if m.district else None,
                "country": "Uganda",
                "kin_full_name": m.surname,
                "kin_phone_number": m.phone_number,
                "registration_date": datetime.now().strftime("%Y-%m-%d"),
                "member_id": m.member_id,
                "is_subscribed_sms": "0"
            }

            mobis = Mobis(m.cooperative.mobis_slug, m.cooperative.mobis_username, m.cooperative.mobis_password)
            mobis_response = mobis.create_individual(params)
            print(mobis_response)
            if not mobis_response.get("error"):
                m.ensuubuko_id = mobis_response.get("data").get("id")
                m.ensuubuko_customer_id = mobis_response.get("data").get("customer_number")
                m.ensuubuko_info = mobis_response
                m.save()

                #     Create Savings Account
                savings_params = {
                    "account_name": m.get_name(),
                    "branch_id": m.cooperative.trust_network_id,
                    "customer_id": m.ensuubuko_id,
                    "opened_at": datetime.now().strftime("%Y-%m-%d"),
                    "opening_balance": 0,
                    "savings_product_id": m.cooperative.saving_product
                }
                mobis_response = mobis.create_savings_account(savings_params)
                if not mobis_response.get("error"):
                    m.ensuubuko_id = mobis_response.get("data").get("id")
                    m.ensuubuko_customer_id = mobis_response.get("data").get("customer_number")
                    m.ensuubuko_info = mobis_response
                    m.save()

                    #     Create Savings Account
                    savings_params = {
                        "account_name": m.get_name(),
                        "branch_id": m.cooperative.trust_network_id,
                        "customer_id": m.ensuubuko_id,
                        "opened_at": datetime.now().strftime("%Y-%m-%d"),
                        "opening_balance": 0,
                        "savings_product_id": 1
                    }
                    savings_response = mobis.create_savings_account(savings_params)
                    if not savings_response.get("error"):
                        m.ensuubuko_savings_id = savings_response.get("data").get("id")
                        m.ensuubuko_savings_product = 1
                        m.save()