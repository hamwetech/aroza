# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import magic
import re
import xlrd
import xlwt
import traceback
from datetime import datetime
import json
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, CharField, Max, Value as V
from django.db.models.functions import Concat
from django.utils.encoding import smart_str
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.views.generic import View, ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormMixin
from django.forms.formsets import formset_factory, BaseFormSet

from messaging.utils import sendSMS
from coop.utils import sendMemberSMS
from conf.utils import log_debug, log_error, generate_alpanumeric, float_to_intstring, get_deleted_objects,\
get_message_template as message_template
from coop.models import *
from activity.models import TrainingAttendance
from product.models import Product, ProductVariation, ProductUnit
from coop.forms import *
from api.Mobis import Mobis
from api.OKOTransactions import OKOTransaction

class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context['active'] = ['_coop_member']
        context['title'] = 'Coop'
        context.update(self.extra_context)
        return context


class MemberDeleteView(ExtraContext, DeleteView):
    model = CooperativeMember
    success_url = reverse_lazy('coop:member_list')
    
    def get_context_data(self, **kwargs):
        #
        context = super(MemberDeleteView, self).get_context_data(**kwargs)
        #
        
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects']=deletable_objects
        context['model_count']=dict(model_count).items()
        context['protected']=protected
        #
        return context


class MemberCreateView(ExtraContext, CreateView):
    template_name = 'coop/memberprofile_form.html'
    model = CooperativeMember
    form_class = MemberProfileForm
    success_url = reverse_lazy('coop:member_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberCreateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs
    
    def form_valid(self, form):
        try:
            form.instance.member_id = self.generate_member_id(form.instance.cooperative)
            form.instance.create_by = self.request.user
            member = super(MemberCreateView, self).form_valid(form)
        except Exception as e:
            form.add_error(None, 'The Phone Number %s exists. Please provide another.' % form.instance.phone_number)
            return super(MemberCreateView, self).form_invalid(form)
        try:
            params = {
                "branch_id": self.object.cooperative.trust_network_id,
                "title": "",
                "first_name": self.object.first_name,
                "surname": self.object.surname,
                "other_name": None,
                "date_of_birth": self.object.date_of_birth.strftime("%Y-%m-%d"),
                "gender": self.object.gender,
                "phone_number": self.object.phone_number,
                "mobile_money_num": None,
                "parish": self.object.village,
                "district": self.object.district.name,
                "country": "Uganda",
                "kin_full_name": self.object.surname,
                "kin_phone_number": self.object.phone_number,
                "registration_date": datetime.now().strftime("%Y-%m-%d"),
                "member_id": self.object.member_id,
                "is_subscribed_sms": "0"
            }
            if self.object.cooperative.mobis_username:
                mobis = Mobis(self.object.cooperative.mobis_slug, self.object.cooperative.mobis_username, self.object.cooperative.mobis_password)
                mobis_response = mobis.create_individual(params)
                print(mobis_response)
                if not mobis_response.get("error"):
                    self.object.ensuubuko_id = mobis_response.get("data").get("id")
                    self.object.ensuubuko_customer_id = mobis_response.get("data").get("customer_number")
                    self.object.ensuubuko_info = mobis_response
                    self.object.save()

                #     Create Savings Account
                    savings_params = {
                        "account_name": self.object.get_name(),
                        "branch_id": self.object.cooperative.trust_network_id,
                        "customer_id": self.object.ensuubuko_id,
                        "opened_at": datetime.now().strftime("%Y-%m-%d"),
                        "opening_balance": 0,
                        "savings_product_id": self.object.cooperative.saving_product
                    }
                    savings_response = mobis.create_savings_account(savings_params)
                    if not savings_response.get("error"):
                        self.object.ensuubuko_savings_id = savings_response.get("data").get("id")
                        self.object.ensuubuko_savings_product = 1
                        self.object.save()

            message = message_template().member_registration
            if message:
                if re.search('<NAME>', message):
                    if member.surname:
                        message = message.replace('<NAME>', '%s %s' % (member.surname.title(), member.first_name.title()))
                    message = message.replace('<COOPERATIVE>', member.cooperative.name)
                    message = message.replace('<IDNUMBER>', member.member_id)
                sendMemberSMS(request, member, message)
        except Exception as e:
            log_error()
            pass
        return member
    
    def generate_member_id(self, cooperative):
        member = CooperativeMember.objects.all()
        count = member.count() + 1
        
        today = datetime.today()
        datem = today.year
        yr = str(datem)[2:]
        # idno = generate_numeric(size=4, prefix=str(m.cooperative.code)+yr)
        # fint = "%04d"%count
        # idno = str(cooperative.code)+yr+fint
        # member = member.filter(member_id=idno)
        idno = self.check_id(member, cooperative, count, yr)
        log_debug("Cooperative %s code is %s" % (cooperative.code, idno))
        return idno
    
    def check_id(self, member, cooperative, count, yr):
        fint = "%04d"%count
        idno = str(cooperative.code)+yr+fint
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            #print "iteration count %s" % count
            return self.check_id(member, cooperative, count, yr)
        return idno


class MemberUpdateView(ExtraContext, UpdateView):
    template_name = 'coop/memberprofile_form.html'
    model = CooperativeMember
    form_class = MemberProfileForm
    success_url = reverse_lazy('coop:member_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberUpdateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs
    
    
def save_transaction(params):
        amount = params.get('amount')
        member = params.get('member')
        transaction_reference = params.get('transaction_reference')
        transaction_type = params.get('transaction_type')
        entry_type = params.get('entry_type')
        
        bal_before = 0
        tq = MemberTransaction.objects.all().order_by('-id')
        if tq.exists():
            bal_before = tq[0].balance_after
        new_bal = amount + bal_before
        MemberTransaction.objects.create(
            member = member,
            transaction_type = transaction_type,
            entry_type = entry_type,
            transaction_reference = transaction_reference, 
            balance_before = bal_before,
            amount = amount,
            balance_after = new_bal
        )
        CooperativeMember.objects.filter(pk=member.id).update(collection_amount=new_bal)
        
               
def load_villages(request):
    sub_county_id = request.GET.get('sub_county')
    villages = Parish.objects.filter(sub_county=sub_county_id).order_by('name')
    return render(request, 'coop/village_dropdown_list_options.html', {'villages': villages})


def load_coop_members(request):
    cooperative_id = request.GET.get('cooperative')
    members = dict()
    if cooperative_id: 
        members = CooperativeMember.objects.filter(cooperative=cooperative_id).order_by('first_name')
    return render(request, 'coop/member_dropdown_list_options.html', {'members': members})


# noinspection PyInterpreter
class MemberUploadExcel(ExtraContext, View):
    template_name = 'coop/upload_member.html'
    
    def get(self, request, *args, **kwargs):
        data = dict()
        data['form'] =  MemberUploadForm
        return render(request, self.template_name, data)
    
    def post(self, request, *args, **kwargs):
        data = dict()
        form = MemberUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['excel_file']
            
            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet'])-1
            startrow = int(form.cleaned_data['row'])-1

            farmer_name_col = int(form.cleaned_data['farmer_name_col'])
            gender_col = int(form.cleaned_data['gender'])
            nin_col = int(form.cleaned_data['nin_col'])
            date_of_birth_col = int(form.cleaned_data['date_of_birth_col'])
            phone_number_col = int(form.cleaned_data['phone_number_col'])
            role_col = int(form.cleaned_data['role_col'])
            year_joined_col = int(form.cleaned_data['year_joined_col'])
            acreage_col = int(form.cleaned_data['acreage_col'])
            cooperative_col = int(form.cleaned_data['cooperative_col'])
            farmer_group_col = int(form.cleaned_data['farmer_group_col'])
            district_col = int(form.cleaned_data['district_col'])
            county_col = int(form.cleaned_data['county_col'])
            sub_county_col = int(form.cleaned_data['sub_county_col'])
            parish_col = int(form.cleaned_data['parish_col'])
            village_col = int(form.cleaned_data['village_col'])
            value_chain_col = int(form.cleaned_data['value_chain_col'])

            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            member_list = []
            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i+1

                    farmer_name = smart_str(row[farmer_name_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\.]+$', farmer_name, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Farmer (row %d)' % \
                                         (farmer_name, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    gender = smart_str(row[gender_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\.]+$', gender, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Gender (row %d)' % \
                                         (gender, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    nin = smart_str(row[nin_col].value).strip()
                    if nin:
                        if not re.search('^[0-9A-Z\s\(\)\-\.]+$', nin, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid NIN (row %d)' % \
                                             (nin, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    date_of_birth = (row[date_of_birth_col].value)
                    if date_of_birth:
                        try:
                            # print(date_of_birth)
                            date_str = datetime(*xlrd.xldate_as_tuple(date_of_birth, book.datemode))
                            date_of_birth = date_str.strftime("%Y-%m-%d")
                        except Exception as e:
                            data['errors'] = '"%s" is not a valid Date of Birth (row %d): %s' % \
                                             (date_of_birth, i + 1, e)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    phone_number = (row[phone_number_col].value)
                    if phone_number:
                        try:
                            phone_number = int(phone_number)
                        except Exception as e:
                            ##print e
                            phone_number = None

                        if phone_number:
                            if not re.search('^[0-9]+$', str(phone_number), re.IGNORECASE):
                                data['errors'] = '"%s" is not a valid Phone Number (row %d)' % \
                                                 (phone_number, i + 1)
                                return render(request, self.template_name,
                                              {'active': 'system', 'form': form, 'error': data})

                    role = smart_str(row[role_col].value).strip()
                    if role:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', role, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Role (row %d)' % \
                                             (role, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    year_joined = smart_str(row[year_joined_col].value).strip()
                    if year_joined:
                        if not re.search('^[0-9]+$', year_joined, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Year Joined (row %d)' % \
                                             (year_joined, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    acreage = smart_str(row[acreage_col].value).strip()
                    if acreage:
                        if not re.search('^[0-9\.]+$', acreage, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid  Acreage (row %d)' % \
                                             (acreage, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    cooperative = smart_str(row[cooperative_col].value).strip()
                    if cooperative:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', cooperative, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Cooperative (row %d)' % \
                                             (cooperative, i + 1)
                            return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                        try:
                            cooperative = Cooperative.objects.get(name=cooperative)
                        except Exception as e:
                            log_error()
                            data['errors'] = 'Cooperative "%s" Not found (row %d)' % \
                                             (cooperative, i + 1)
                            return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    farmer_group = smart_str(row[farmer_group_col].value).strip()
                    if farmer_group:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', farmer_group, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Farmer Group (row %d)' % \
                                             (farmer_group, i + 1)
                            return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                        try:
                            farmer_group = FarmerGroup.objects.get(name=farmer_group)
                        except Exception as e:
                            log_error()
                            data['errors'] = 'Farmer Group "%s" Not found (row %d)' % \
                                             (farmer_group, i + 1)
                            return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    if not cooperative and farmer_group:
                        data['errors'] = 'Cooperative of Farmer Group not Provided'
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    district = smart_str(row[district_col].value).strip()

                    if district:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', district, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid District (row %d)' % \
                                             (district, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    county = smart_str(row[county_col].value).strip()#.decode('utf-8')

                    if county:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', county, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid County (row %d)' % \
                                             (county, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    sub_county = smart_str(row[sub_county_col].value).strip()

                    if sub_county:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', sub_county, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Sub County (row %d)' % \
                                             (sub_county, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    parish = smart_str(row[parish_col].value).strip()

                    if parish:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', parish, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Parish (row %d)' % \
                                             (parish, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    village = smart_str(row[village_col].value).strip()

                    if village:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', village, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Village (row %d)' % \
                                             (village, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    value_chain = smart_str(row[value_chain_col].value).strip()
                    if value_chain:
                        if not re.search('^[A-Z\s\(\)\-\.\,\|]+$', value_chain, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Value Chain (row %d)' % \
                                             (value_chain, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    q = {
                        'farmer_name': farmer_name,
                        'gender': gender,
                        'nin': nin,
                        'date_of_birth': date_of_birth,
                        'phone_number': phone_number,
                        'role': role,
                        'year_joined': year_joined,
                        'acreage': acreage,
                        'cooperative': cooperative,
                        'farmer_group': farmer_group,
                        'district': district,
                        'county': county,
                        'sub_county': sub_county,
                        'parish': parish,
                        'village': village,
                        'value_chain': value_chain
                    }
                    member_list.append(q)
                
                except Exception as err:
                    log_error()
                    print(traceback.format_exc())
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': "%s (row %d)" % (err, i+1)})
            if member_list:
                with transaction.atomic():
                    try:
                        do = None
                        sco = None
                        co = None
                        po = None
                        for c in member_list:
                            name = c.get('farmer_name').split(' ')
                            surname = name[0]
                            first_name = name[1] if len(name) > 1 else None
                            other_name = name[2] if len(name) > 2 else None
                            nin = c.get('nin')
                            cooperative = c.get('cooperative')
                            farmer_group = c.get('farmer_group')
                            district = c.get('district')
                            sub_county = c.get('sub_county')
                            county = c.get('county')
                            parish = c.get('parish')
                            village = c.get('village')
                            value_chain = c.get('value_chain')
                            acreage = c.get('acreage') if c.get('acreage') != '' else 0
                            phone_number = c.get('phone_number')
                            gender = c.get('gender')
                            role = c.get('role')
                            year_joined = c.get('year_joined')
                            date_of_birth = c.get('date_of_birth') if c.get('date_of_birth') != '' else None

                            if district:
                                dl = [dist for dist in District.objects.filter(name__iexact=district)]
                                do = dl[0] if len(dl) > 0 else None

                            if county:
                                cl = [c for c in County.objects.filter(district__name=district, name=county)]
                                co = cl[0] if len(cl) > 0 else None

                            if sub_county:
                                scl = [subc for subc in SubCounty.objects.filter(county__name=county, name=sub_county)]
                                sco = scl[0] if len(scl) > 0 else None

                            if parish:
                                pl = [p for p in Parish.objects.filter(sub_county__name=sub_county, name=parish)]
                                po = pl[0] if len(pl) > 0 else None

                            if not CooperativeMember.objects.filter(first_name=first_name, surname=surname,
                                                                    phone_number=phone_number).exists():
                                member = CooperativeMember.objects.create(
                                    # cooperative=cooperative,
                                    surname=surname,
                                    first_name=first_name,
                                    other_name=other_name,
                                    id_number=nin if nin else None,
                                    gender=gender,
                                    cooperative=cooperative,
                                    farmer_group=farmer_group if farmer_group != '' else None,
                                    date_of_birth=date_of_birth,
                                    phone_number=phone_number if phone_number != '' else None,
                                    district=do,
                                    county=co,
                                    sub_county=sco,
                                    parish=po,
                                    village=village,
                                    product=value_chain,
                                    coop_role=role.title(),
                                    land_acreage=acreage if acreage else 0,
                                    year_joined=year_joined if year_joined else None,
                                    create_by=request.user
                                )
                                member.member_id = self.generate_member_id(member)
                                member.save()
                                #if message:
                                #    if re.search('<NAME>', message):
                                #        if member.surname:
                                #            message = message.replace('<NAME>', '%s %s' % (member.surname.title(), member.first_name.title()))
                                #        message = message.replace('<COOPERATIVE>', member.cooperative.name)
                                #        message = message.replace('<IDNUMBER>', member.member_id)
                                #    sendMemberSMS(request, member, message)
                                                    
                        return redirect('coop:member_list')
                    except Exception as err:
                        log_error()
                        data['error'] = err
                
        data['form'] = form
        return render(request, self.template_name, data)
    

    def generate_member_id(self, instance):
        today = datetime.today()
        datem = today.year
        yr = str(datem)[2:]
        m = datetime.today().strftime("%m")
        member = CooperativeMember.objects.all()
        count = instance.id
        fint = "%04d" % count
        idno = "D{}{}{}{}".format(instance.gender[:1], yr, m, fint)
        idno = self.check_id(idno, member)
        print("ID %s " % (idno))
        return idno

    def check_id(self, idno, member):
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            return self.check_id(idno)
        return idno


class CooperativeMemberListView(ExtraContext, ListView):
    model = CooperativeMember
    template_name = 'coop/cooperativemember_list.html'
    ordering = ['-id']
    
    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(CooperativeMemberListView, self).dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super(CooperativeMemberListView, self).get_queryset()
        msisdn = self.request.GET.get('phone_number')
        name = self.request.GET.get('name')
        coop = self.request.GET.get('cooperative')
        role = self.request.GET.get('role')
        district = self.request.GET.get('district')
        create_by = self.request.GET.get('create_by')

        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            queryset = queryset.filter(cooperative=cooperative)
        if msisdn:
            queryset = queryset.filter(phone_number='%s' % msisdn)
        if name:
            #name=Concat('surname',V(' '),'first_name',V(' '),'other_name')
            queryset = queryset.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
            #queryset = queryset.filter(Concat(surname,V(' '),first_name,V(' '),other_name)=name)
        if coop:
            queryset = queryset.filter(cooperative__id=coop)
        if role:
            queryset = queryset.filter(coop_role=role)
        if district:
            queryset = queryset.filter(district__id=district)
        if create_by:
            queryset = queryset.filter(create_by__profile__id=create_by)
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super(CooperativeMemberListView, self).get_context_data(**kwargs)
        context['form'] = MemberProfileSearchForm(self.request.GET, request=self.request)
        return context
    
    def download_file(self, *args, **kwargs):
        
        _value = []
        columns = []
        msisdn = self.request.GET.get('phone_number')
        name = self.request.GET.get('name')
        coop = self.request.GET.get('cooperative')
        role = self.request.GET.get('role')
        district = self.request.GET.get('district')
        create_by = self.request.GET.get('create_by')

        
        profile_choices = ['id','cooperative__name', 'member_id', 'surname', 'first_name', 'other_name',
                               'date_of_birth', 'gender', 'is_refugee', 'is_handicap', 'phone_number','product',
                               'district__name','sub_county__name','village','address','gps_coodinates',
                               'coop_role','land_acreage', 'shares',
                               'collection_amount','collection_quantity', 'paid_amount', 'create_by__username', 'create_date']

        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
        #Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that 
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')
        
        # The response also has additional Content-Disposition header, which contains 
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=CooperativeMembers_%s.xls' % datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Create object for the Workbook which is under xlwt library.
        workbook = xlwt.Workbook()
        
        # By using Workbook object, add the sheet with the name of your choice.
        worksheet = workbook.add_sheet("Members")

        row_num = 0
        style_string = "font: bold on; borders: bottom dashed"
        style = xlwt.easyxf(style_string)

        for col_num in range(len(columns)):
            # For each cell in your Excel Sheet, call write function by passing row number, 
            # column number and cell data.
            worksheet.write(row_num, col_num, columns[col_num], style=style)
        
        
        _members = CooperativeMember.objects.values(*profile_choices).all()
        
        if msisdn:
            _members = _members.filter(phone_number='%s' % msisdn)
        if name:
            _members = _members.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
        if coop:
            _members = _members.filter(cooperative__id=coop)
        if role:
            _members = _members.filter(coop_role=role)
        if district:
            _members = _members.filter(district__id=district)
        if create_by:
            _members = _members.filter(create_by__profile__id=create_by)
        
        for m in _members:
            
            
            row_num += 1
            # ##print profile_choices
            # row = [m['%s' % x] if 'date_of_birth' not in x else m['%s' % x].strftime('%d-%m-%Y') if m.get('%s' % x) else ""  for x in profile_choices]
            row_ = []
            for x in profile_choices:
                if m.get('%s' % x):
                    if 'date_of_birth' in x:
                        #row_.append(datetime.strpdate(str(m.get('%s' % x)), '%Y-%m-%d'))
                        row_.append(str(m.get('%s' % x)))
                    elif 'create_date' in x:
                        #row_.append(datetime.strptime(str(m.get('%s' % x))[:19], '%Y-%m-%d %H:%M:%S'))
                        row_.append(str(m.get('%s' % x))[:19])
                    else:
                        row_.append(m.get('%s' % x))
                else:
                    row_.append("")
            for col_num in range(len(row_)):
                worksheet.write(row_num, col_num, row_[col_num])
        workbook.save(response)
        return response
    
    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces :
            # Check if string is in the main string
            if elem in mainString :
                # Replace the string
                mainString = mainString.replace(elem, newString)
        
        return  mainString


class ImageQRCodeDownloadView(View):
    def get(self, request, *args, **kwargs):
        try:
            pk = self.kwargs.get('pk')
            qs = CooperativeMember.objects.get(pk=pk)
            image = qs.get_qrcode()
            ##print image.path
            image_buffer = open(image.path, "rb").read()
            content_type = magic.from_buffer(image_buffer, mime=True)
            response = HttpResponse(image_buffer, content_type=content_type);
            response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(image.path)
            return response
        except Exception:
            log_error()
            return redirect('coop:member_list') 


class DeprecatedDownloadExcelMemberView(View):
    template_name = 'coop/download_member.html'
    
    def get(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm(request.POST)
        if form.is_valid():
            _value = []
            profile = form.cleaned_data.get('profile')
            # farm = form.cleaned_data.get('farm')
            # deworming = form.cleaned_data.get('deworming')
            # breed = form.cleaned_data.get('breed')
            # bull_herd = form.cleaned_data.get('bull_herd')
            # cow_herd = form.cleaned_data.get('cow_herd')
            # member_supply = form.cleaned_data.get('member_supply')
            _value += profile
            # _value+= farm
            # _value += deworming
            # _value += breed
            # _value += bull_herd
            # _value += cow_herd
            # _value += member_supply
            if len(profile) > 0:
                _members = CooperativeMember.objects.values(*[x for x in profile]).all()
                for m in _members:
                    if len(farm) > 0:
                        _biz = CooperativeMemberBusiness.objects.values(*[x for x in farm]).filter(cooperative_member=m)
                    if len(deworming) > 0:
                        _deworm = DewormingSchedule.objects.values(*[x for x in deworming]).filter(cooperative_member=m)
                    if len(breed) > 0:
                        _breeds = CooperativeMemberProductDefinition.objects.values(*[x for x in deworming]).filter(cooperative_member=m)
                    if len(bull_herd) > 0:
                        _bulls = CooperativeMemberHerdMale.objects.values(*[x for x in bull_herd]).filter(cooperative_member=m)
                    if len(cow_herd) > 0:
                        _cows = CooperativeMemberHerdFemale.objects.values(*[x for x in cow_herd]).filter(cooperative_member=m)
                    if len(member_supply) > 0:
                        deworm = CooperativeMemberSupply.objects.values(*[x for x in member_supply]).filter(cooperative_member=m)
                
            raise Exception(len(farm))
        return render(request, self.template_name, {'form': form})


class DownloadExcelMemberView(View):
    template_name = 'coop/download_member.html'
    
    def get(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm(request.POST)
        if form.is_valid():
            _value = []
            profile = form.cleaned_data.get('profile')
            farm = form.cleaned_data.get('farm')
            herd = form.cleaned_data.get('herd')
            member_supply = form.cleaned_data.get('member_supply')
            columns = []
            
            profile_choices = ['id','cooperative__name', 'member_id', 'surname', 'first_name', 'other_name',
                               'date_of_birth', 'gender', 'maritual_status','phone_number','email',
                               'district__name','sub_county__name','village','address','gps_coodinates',
                               'coop_role','cotton_acreage', 'soya_beans_acreage','soghum_acreage','shares',
                               'collection_amount','collection_quantity', 'paid_amount']
            
            farm_choices = ['business_name', 'farm_district__name','farm_sub_county__name', 'gps_coodinates',
                            'size', 'fenced', 'paddock','water_source',
                            'animal_identification','common_diseases','other_animal_diseases','tick_control']
    
            male_herd = ['adults', 'bullocks', 'calves']
            female_herd = ['f_adults', 'heifers', 'f_calves']
            member_supply_choice = ['nearest_market','product_average_cost','price_per_kilo','probable_sell_month',
                              'probable_sell_month', 'sell_to_cooperative_society']
            
            columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
            if farm:
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in farm_choices]
                columns += ['Deworm Schedule']
            if herd:
                columns += ['Breeds']
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in male_herd]
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in female_herd]
            if member_supply:
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in member_supply_choice]
            #Gather the Information Found
            # Create the HttpResponse object with Excel header.This tells browsers that 
            # the document is a Excel file.
            response = HttpResponse(content_type='application/ms-excel')
            
            # The response also has additional Content-Disposition header, which contains 
            # the name of the Excel file.
            response['Content-Disposition'] = 'attachment; filename=CooperativeMembers_%s.xls' % datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Create object for the Workbook which is under xlwt library.
            workbook = xlwt.Workbook()
            
            # By using Workbook object, add the sheet with the name of your choice.
            worksheet = workbook.add_sheet("Members")

            row_num = 0
            style_string = "font: bold on; borders: bottom dashed"
            style = xlwt.easyxf(style_string)

            for col_num in range(len(columns)):
                # For each cell in your Excel Sheet, call write function by passing row number, 
                # column number and cell data.
                worksheet.write(row_num, col_num, columns[col_num], style=style)
            
            if profile:
                _members = CooperativeMember.objects.values(*profile_choices).all()
                
                for m in _members:
                    
                    if farm:
                        _biz = CooperativeMemberBusiness.objects.values(*farm_choices).filter(cooperative_member=m['id'])
                        _deworm = DewormingSchedule.objects.values('deworm_date','dewormer').filter(cooperative_member=m['id'])
                    if herd:
                        _breeds = CooperativeMemberProductDefinition.objects.filter(cooperative_member=m['id'])
                        _bulls = CooperativeMemberHerdMale.objects.values(*male_herd).filter(cooperative_member=m['id'])
                        _cows = CooperativeMemberHerdFemale.objects.values(*female_herd).filter(cooperative_member=m['id'])
                    if member_supply:
                        _member_supply = CooperativeMemberSupply.objects.values(*member_supply_choice).filter(cooperative_member=m['id'])
                    
                    row_num += 1
                    row = [m['%s' % x] for x in profile_choices]
                    if farm:
                        if _biz.exists():
                            row += [_biz[0]['%s' % x] for x in farm_choices]
                        if _deworm.exists():
                            row += [','.join(['%s | %s' % (dw['deworm_date'], dw['dewormer']) for dw in _deworm])]
                    if herd:
                        if _breeds.exists():
                            row += ['|'.join([brd.name for brd in _breeds[0].product_variation.all()])]
                        if _bulls.exists():
                            row += [_bulls[0]['%s' % x] for x in male_herd]
                        if _cows.exists():
                            row += [_cows[0]['%s' % x] for x in female_herd]
                    if member_supply:
                        if _member_supply.exists():
                            row += [_member_supply[0]['%s' % x] for x in member_supply_choice]
                    for col_num in range(len(row)):
                        worksheet.write(row_num, col_num, row[col_num])
                workbook.save(response)
                return response
                                        
            
        return render(request, self.template_name, {'form': form})

    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces :
            # Check if string is in the main string
            if elem in mainString :
                # Replace the string
                mainString = mainString.replace(elem, newString)
        
        return  mainString


class SendCommunicationView(View):
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SendCommunicationView, self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        msisdn = self.request.GET.get('phone_number')
        name = self.request.GET.get('name')
        coop = self.request.GET.get('cooperative')
        role = self.request.GET.get('role')
        district = self.request.GET.get('district')
        jres = {'status': 'error', 'message': 'Unknown Error! Message not sent. Contact Admin.'}
        try:
            queryset =  CooperativeMember.objects.all()
            if not request.user.profile.is_union():
                queryset = queryset.filter(cooperative = request.user.cooperative_admin.cooperative)
            response = ""
            if msisdn:
                queryset = queryset.filter(phone_number='%s' % msisdn)
                response += "Phone Number " + msisdn
            if name:
                queryset = queryset.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
                response += " Name "
            if coop:
                queryset = queryset.filter(cooperative__id=coop)
                c = Cooperative.objects.get(pk=coop)
                response += " Cooperative "+c.name
            if role:
                queryset = queryset.filter(coop_role=role)
                response += " Role " + role
            if district:
                queryset = queryset.filter(district__id=district)
                d = District.objects.get(pk=district)
                response += " District " + d.name    
            response += "<div>Total Messages %s</div>" % queryset.count()
            jres = {'status': 'success', 'message': response}
        except Exception:
            log_error()
            jres = {'status': 'error', 'message': 'Error! Messages not Sent.'}
            
        return JsonResponse(jres)
    
    def post(self, request,  *args, **kwargs):
        ##print " Message: %s" % (self.request.body)
        body_unicode = self.request.body.decode('utf-8')
        data = json.loads(body_unicode)
        
        msisdn = data.get('phone_number')
        name = data.get('name')
        coop = data.get('cooperative')
        role = data.get('role')
        district = data.get('district')
        jres = {'status': 'error', 'message': 'Unknown Error! Message not sent. Contact Admin.'}
        
        try:
            queryset =  CooperativeMember.objects.all()
            if not request.user.profile.is_union():
                queryset = queryset.filter(cooperative = request.user.cooperative_admin.cooperative)
            if msisdn:
                queryset = queryset.filter(phone_number='%s' % msisdn)
            if name:
                queryset = queryset.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
            if coop:
                queryset = queryset.filter(cooperative__id=coop)
            if role:
                queryset = queryset.filter(coop_role=role)
            if district:
                queryset = queryset.filter(district__id=district)
            
            for q in queryset:
                count = 0
                message = data.get('message')
                msisdn = q.phone_number
                if re.search('<NAME>', message):
                    if q.surname:
                        message = message.replace('<NAME>', q.surname.title())
                #print "%s Message: %s" % (q.phone_number, message)
                sms = sendMemberSMS(self.request, q, message)
                if sms:
                    count += 1
            jres = {'status': 'success', 'message': '%s Messages sent. <div><small>If some messages were not sent, Please check the send Message status of the Cooperative</small</div>' % count}
        except Exception:
            log_error()
            jres = {'status': 'error', 'message': 'Error! Message not sent. Contact Admin.'}
        return JsonResponse(jres)
    
    
class CooperativeMemberDetailView(ExtraContext, DetailView):
    model = CooperativeMember
    
    def get_queryset(self):
        qs = super(CooperativeMemberDetailView, self). get_queryset()
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            qs = qs.filter(cooperative=cooperative) 
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(CooperativeMemberDetailView, self).get_context_data(**kwargs)
        context['training'] = TrainingAttendance.objects.filter(coop_member__id=self.kwargs.get('pk'))
        #raise Exception(context['training'])
        return context
    

class MemberSubscriptionListView(ExtraContext, ListView):
    model = CooperativeMemberSubscriptionLog
    

class MemberSubscriptionCreateView(ExtraContext, CreateView):
    model = CooperativeMemberSubscriptionLog
    form_class = MemberSubscriptionForm
    success_url = reverse_lazy('coop:member_subscription_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.transaction_id = generate_alpanumeric()
        bal_before = form.instance.cooperative_member.subscription_amount
        bal_after = bal_before + form.instance.amount_paid
        form.instance.cooperative_member.subscription_amount = bal_after
        form.instance.cooperative_member.save()
        # form.instance.new_balance = bal_after
        return super(MemberSubscriptionCreateView, self).form_valid(form)
    
    
class MemberSubscriptionUpdateView(ExtraContext, UpdateView):
    model = CooperativeMemberSubscriptionLog
    form_class = MemberSubscriptionForm
    success_url = reverse_lazy('coop:member_subscription_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cont = CooperativeMemberSubscriptionLog.objects.get(pk=form.instance.id)
        acc_bal = form.instance.cooperative_member.subscription_amount
        deducted = acc_bal - cont.amount_paid
        final = deducted + form.instance.amount_paid
        form.instance.cooperative_member.subscription_amount = final
        form.instance.cooperative_member.save()
        # form.instance.new_balance = final
        return super(MemberSubscriptionUpdateView, self).form_valid(form)


class MemberSharesView(ListView):
    model = CooperativeMemberSharesLog
    template_name = 'coop/MemberShares.html'
    
    def get_queryset(self):
        queryset = CooperativeMemberSharesLog.objects
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            queryset = queryset.filter(cooperative_member__cooperative = cooperative)
        queryset = queryset.values('cooperative_member',
                                   name=Concat('cooperative_member__surname',
                                               V(' '),
                                               'cooperative_member__first_name'
                                               ),
                                   
                                   ).annotate(total_amount=Sum('amount'), total_shares=Sum('shares'), transaction_date=Max('transaction_date')).order_by('-transaction_date')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(MemberSharesView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_member_shares']
        return context


class MemberSharesListView(ExtraContext, ListView):
    model = CooperativeMemberSharesLog
    template_name = 'coop/cooperativemembersharelog_list.html'
    
    def get_queryset(self):
        queryset = CooperativeMemberSharesLog.objects.all()
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            queryset = queryset.filter(cooperative_member__cooperative=cooperative)
        member = self.kwargs.get('member')
        if member:
            queryset = queryset.filter(cooperative_member=member)
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super(MemberSharesListView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_member_shares']
        return context
    

class MemberSharesCreateView(CreateView):
    model = CooperativeMemberSharesLog
    form_class = MemberSharesForm
    success_url = reverse_lazy('coop:member_shares_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberSharesCreateView, self).get_form_kwargs()
        kwargs['request'] = self.request # pass the 'user' in kwargs
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.transaction_id = generate_alpanumeric()
        bal_before = form.instance.cooperative_member.shares
        amt_before = form.instance.cooperative_member.share_amount
        bal_after = bal_before + form.instance.shares
        amt_after = amt_before + form.instance.amount
        form.instance.cooperative_member.shares = bal_after
        form.instance.cooperative_member.share_amount = amt_after
        form.instance.cooperative_member.save()
        form.instance.new_shares = bal_after
        member = form.instance.cooperative_member
        try:
            message = message_template().member_share_purchase
            message = message.replace('<NAME>', member.surname)
            message = message.replace('<SHARES>', '%s' % form.instance.shares)
            message = message.replace('<AMOUNT>', '%s' % form.instance.amount)
            message = message.replace('<TOTAL>', '%s' %  bal_after)
            message = message.replace('<REFERENCE>', form.instance.transaction_id)
            sendMemberSMS(self.request, member, message)
        except Exception:
            log_error()
        return super(MemberSharesCreateView, self).form_valid(form)
    
    
class MemberSharesUpdateView(UpdateView):
    model = CooperativeMemberSharesLog
    form_class = MemberSharesForm
    success_url = reverse_lazy('coop:member_shares_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberSharesUpdateView, self).get_form_kwargs()
        kwargs['request'] = self.request # pass the 'user' in kwargs
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cont = CooperativeMemberSharesLog.objects.get(pk=form.instance.id)
        acc_bal = form.instance.cooperative_member.shares
        deducted = acc_bal - cont.shares
        final = deducted + form.instance.shares
        form.instance.cooperative_member.shares = final
        form.instance.cooperative_member.save()
        form.instance.new_shares = final
        return super(MemberSharesUpdateView, self).form_valid(form)
    

class MemberSupplyRequestListView(ListView):
    model = MemberSupplyRequest
    ordering = ['-create_date']
    
    def get_queryset(self):
        queryset = super(MemberSupplyRequestListView, self).get_queryset()
        
        if not self.request.user.profile.is_union():
            if not self.request.user.profile.is_partner():
                cooperative = self.request.user.cooperative_admin.cooperative 
                queryset = queryset.filter(cooperative_member__cooperative=cooperative)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(MemberSupplyRequestListView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_supply_request', '']
        return context
    
    
class MemberSupplyRequestCreateView(View):
    
    template_name = 'coop/membersupplyrequest_form.html'
    
    def get(self, request, *args, **kwargs):
        initial = None
        supply = None
        extra = 1
        pk = self.kwargs.get('pk')
        if pk:
            supply = MemberSupplyRequest.objects.get(pk=pk)
            pvars = MemberSupplyRequestVariation.objects.filter(supply_request=supply)
            initial = [{'breed': x.breed, 'total': x.total} for x in pvars]
            extra = 0 if len(initial) > 0 else 1
        
        form = MemberSupplyRequestForm(instance=supply, request=request)
        
        variation_formset = formset_factory(MemberSupplyRequestVariationForm, formset=VariationSupplyRequestFormSet, extra=extra)
        variation_form = variation_formset(prefix='variation', initial=initial)
        return render(request, self.template_name, {'form': form, 'variation_form': variation_form, 'active': ['_coop_supply_request', '']})
    
    def post(self, request, *args, **kwargs):
        initial = None
        supply = None
        extra = 1
        pk = self.kwargs.get('pk')
        if pk:
            supply = MemberSupplyRequest.objects.get(pk=pk)
            pvars = MemberSupplyRequestVariation.objects.filter(supply_request=supply)
            initial = [{'breed': x.breed, 'total': x.total} for x in pvars]
            extra = 0 if len(initial) > 0 else 1
        form = MemberSupplyRequestForm(request.POST, request=request, instance=supply)
        variation_formset = formset_factory(MemberSupplyRequestVariationForm, formset=VariationSupplyRequestFormSet, extra=extra)
        variation_form = variation_formset(request.POST, prefix='variation', initial=initial)
        if form.is_valid() and variation_form.is_valid():
            try:
                with transaction.atomic():
                    
                    req = form.save(commit=False)
                    if not pk:
                        req.transaction_reference = generate_alpanumeric(prefix="SR", size=8)
                    req.created_by = request.user
                    req.save()
                    if pk:
                        MemberSupplyRequestVariation.objects.filter(supply_request=req).delete()
                    for c in variation_form:
                        if len(c.cleaned_data) > 0:
                            cf = c.save(commit=False)
                            cf.supply_request = req
                            cf.created_by = request.user
                            cf.save()
                    
                    try:
                        message = message_template().supply_request
                        message = message.replace('<NAME>', req.cooperative_member.surname)
                        message = message.replace('<NUMBER>', '%s' % req.get_sum_total())
                        message = message.replace('<DATE>', '%s' % req.supply_date)
                        message = message.replace('<REFERENCE>', req.transaction_reference)
                        sendMemberSMS(self.request, req.cooperative_member, message)
                    except Exception:
                        log_error()
                    return redirect('coop:request_list')
                    
            except Exception as e:
                form.add_error(None, "Supply Request Error! Contact Admin")
                log_error()
        return render(request, self.template_name, {'form': form, 'variation_form': variation_form, 'active': ['_coop_supply_request', '']})
      
    
class MemberSupplyRequestDetailView(FormMixin, DetailView):
    model = MemberSupplyRequest
    form_class = MemberSupplyRequestConfirmForm
    
    def get_success_url(self):
        return reverse('coop:request_list')
    
    def get_context_data(self, **kwargs):
        context = super(MemberSupplyRequestDetailView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_supply_request', '']
        instance = MemberSupplyRequest.objects.get(pk=self.kwargs.get('pk'))
        context['form'] = MemberSupplyRequestConfirmForm(instance = instance)
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        instance = MemberSupplyRequest.objects.get(pk=self.kwargs.get('pk'))
        form = MemberSupplyRequestConfirmForm(request.POST, instance = instance)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        # Here, we would record the user's interest using the message
        # passed in form.cleaned_data['message']
        form.instance.confirmation_logged_by = self.request.user
        form.save()
        
        try:
            message = message_template().supply_confirmation
            if form.instance.status == 'ACCEPTED':
                message = message.replace('<NAME>', form.instance.cooperative_member.surname)
                message = message.replace('<DATE>', '%s' % form.instance.supply_date)
                message = message.replace('<REFERENCE>', form.instance.transaction_reference)
                
            else:
                message = message_template().supply_cancelled
                message = message.replace('<NAME>', form.instance.cooperative_member.surname)
                message = message.replace('<REFERENCE>', form.instance.transaction_reference)
            sendMemberSMS(self.request, form.instance.cooperative_member, message)
        except Exception:
            log_error()
        messages.success(self.request, 'Request %s Confirmed' % form.instance.transaction_reference)
        return super(MemberSupplyRequestDetailView, self).form_valid(form)


class SupplyConfirmationView(UpdateView):
    model = MemberSupplyRequest
    form_class = MemberSupplyRequestConfirmForm
    
    def get_context_data(self, **kwargs):
        context = super(SupplyConfirmationView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_supply_request', '']
        return context


class MembersMapView(TemplateView):
    template_name = "coop/farmer_map.html"


def get_farmer_map(request):
    farmer = CooperativeMember.objects.all()
    data = []
    for f in farmer:
        if f.gps_coodinates:
            data.append({"name": f.get_name(), "gps": f.gps_coodinates})
    print(data)
    return JsonResponse(data, safe=False)


class OKOListView(ListView):
    model = OKOMemberPolicy


class OKOCreatePolicyView(View):

    def get(self, request, **kwargs):
        member = CooperativeMember.objects.get(pk=self.kwargs.get('pk'))
        payload = {
            "district": {
                "name": member.district.name if member.district  else ""
            },
            "county": "",
            "sub_county": member.sub_county.name if member.sub_county  else "" ,
            "member_id": member.member_id,
            "surname": member.surname,
            "first_name": member.first_name,
            "other_name": member.other_name if member.other_name else "",
            "gender": member.gender,
            "date_of_birth": member.date_of_birth.strftime('%Y-%m-%d') if member.date_of_birth else "",
            "phone_number": member.phone_number.replace("256", "") if member.phone_number else "",
            "land_acreage": str(member.land_acreage) if member.land_acreage else ""
        }
        try:
            oko = OKOTransaction()
            res = oko.CreatePolicyPartner(payload)

            if "policyId" in res and res.get('policyId'):
                policyId = res.get('policyId')
                amountDue = res.get('amountDue')

                qs = OKOMemberPolicy.objects.filter(policyId=policyId)
                if qs.exists():
                    qs = qs[0]
                    qs.amount_due = amountDue
                    qs.save()
                else:
                    OKOMemberPolicy.objects.create(
                        cooperative_member=member,
                        policyId = policyId,
                        amount_due = amountDue,
                        created_by = request.user
                    )
                messages.success(self.request, "Policy created.")
        except Exception as e:
            log_error()
            messages.error(self.request, "Policy creation failed.")

        return redirect('coop:member_detail', pk=member.id)


class OKOCheckPolicyView(View):

    def get(self, request, **kwargs):
        from django.utils.dateparse import parse_datetime
        pk = self.kwargs.get('pk')
        okop = OKOMemberPolicy.objects.get(pk=pk)
        # {u'totalPaid': 0.0, u'endDate': u'2022-09-21T00:00:00', u'amountLeft': 123000.0, u'claimStatus': 1}
        try:
            oko = OKOTransaction()
            res = oko.ChecckPolicy(okop.policyId)
            okop.amount_paid = res.get('totalPaid')
            okop.amount_due = res.get('amountLeft')
            okop.claim_status = res.get('claimStatus')
            datetime_object = parse_datetime(res.get('endDate'))
            okop.end_date = datetime_object
            okop.save()
            return redirect('coop:member_detail', pk=okop.cooperative_member.id)
        except Exception as e:
            log_error()
            messages.error(self.request, "Policy Check failed.")
            return redirect('coop:member_detail', pk=okop.cooperative_member.id)

