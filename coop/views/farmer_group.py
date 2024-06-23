# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import xlrd
import datetime
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.encoding import smart_str
from django.db import transaction
from django.db.models import Count, Q
from django.views.generic import View, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from conf.utils import log_debug, log_error, get_deleted_objects, get_consontant_upper, generate_numeric
from conf.models import District, County, SubCounty
from coop.models import *
from coop.forms import *


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context


class FarmerGroupListView(ExtraContext, ListView):
    model = FarmerGroup
    extra_context = {'active': ['_farmer_group']}

    def get_queryset(self, **kwargs):
        queryset = super(FarmerGroupListView, self).get_queryset(**kwargs)
        return queryset


class FarmerGroupCreateView(ExtraContext, CreateView):
    model = FarmerGroup
    form_class = FarmerGroupForm
    extra_context = {'active': ['_farmer_group']}
    success_url = reverse_lazy('coop:fg_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.code = self.check_code(form)
        return super(FarmerGroupCreateView, self).form_valid(form)

    def check_code(self, form):
        code = get_consontant_upper(form.instance.name)
        q = FarmerGroup.objects.filter(code=code)
        if q.exists():
            count = q.count()
            q2 = FarmerGroup.objects.filter(code__contains=form.instance.name.upper()[:3])
            code = "%s%s" % (form.instance.name.upper()[:3], generate_numeric(size=2))
            return code
        return get_consontant_upper(form.instance.name)

    def get_form_kwargs(self):
        kwargs = super(FarmerGroupCreateView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class FarmerGroupUpdateView(ExtraContext, UpdateView):
    model = FarmerGroup
    form_class = FarmerGroupForm
    extra_context = {'active': ['_farmer_group']}
    success_url = reverse_lazy('coop:fg_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(FarmerGroupUpdateView, self).form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(FarmerGroupUpdateView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class FarmerGroupDeleteView(ExtraContext, DeleteView):
    model = FarmerGroup
    extra_context = {'active': ['_farmer_group']}
    success_url = reverse_lazy('coop:fg_list')
    template_name = "confirm_delete.html"

    def get_context_data(self, **kwargs):
        #
        context = super(FarmerGroupDeleteView, self).get_context_data(**kwargs)
        #
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects'] = deletable_objects
        context['model_count'] = dict(model_count).items()
        context['protected'] = protected
        #
        return context


class FarmerGroupUploadView(View):
    template_name = 'coop/upload_fg.html'

    def get(self, request, *arg, **kwargs):
        data = dict()
        data['form'] = FarmerGroupUploadForm(request=request)
        data['active'] = ['_farmer_group']
        return render(request, self.template_name, data)

    def post(self, request, *args, **kwargs):
        data = dict()
        form = FarmerGroupUploadForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            # partner = form.cleaned_data['partner']
            f = request.FILES['excel_file']

            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet']) - 1
            startrow = int(form.cleaned_data['row']) - 1
            cooperative_col = int(form.cleaned_data['cooperative_col'])
            district_col = int(form.cleaned_data['district_col'])
            # county_col = int(form.cleaned_data['county_col'])
            sub_county_col = int(form.cleaned_data['sub_county_col'])
            parish_col = int(form.cleaned_data['parish_col'])
            village_col = int(form.cleaned_data['village_col'])
            contact_person_col = int(form.cleaned_data['contact_person'])
            phone_number_col = int(form.cleaned_data['phone_number'])

            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            cooperative_list = []
            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i + 1
                    cooperative = smart_str(row[cooperative_col].value).strip()

                    if not re.search('^[0-9A-Z\s\(\)\-\.]+$', cooperative, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Farmer Group (row %d)' % \
                                         (cooperative, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    district = smart_str(row[district_col].value).strip()

                    if district:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', district, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid District (row %d)' % \
                                             (district, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    # county = smart_str(row[county_col].value).strip()
                    #
                    # if county:
                    #     if not re.search('^[A-Z\s\(\)\-\.]+$', county, re.IGNORECASE):
                    #         data['errors'] = '"%s" is not a valid County (row %d)' % \
                    #                          (county, i + 1)
                    #         return render(request, self.template_name,
                    #                       {'active': 'system', 'form': form, 'error': data})

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

                    contact_person = smart_str(row[contact_person_col].value).strip()
                    if contact_person:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', contact_person, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Contact Person (row %d)' % \
                                             (contact_person, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})
                    phone_number = smart_str(row[phone_number_col].value).strip()

                    if phone_number:
                        try:
                            phone_number = int(row[phone_number_col].value)
                        except Exception:
                            data['errors'] = '"%s" is not a valid Phone number (row %d)' % \
                                             (phone_number, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    q = {'name': cooperative, 'district': district, 'sub_county': sub_county, 'parish': parish, 'village': village,
                         'contact_person': contact_person, 'phone_number': phone_number}
                    cooperative_list.append(q)

                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form': form, 'error': '%s on (row %d)' % (err, i + 1)})
            if cooperative_list:
                with transaction.atomic():
                    try:
                        do = None
                        sco = None
                        po = None

                        for c in cooperative_list:
                            name = c.get('name')
                            district = c.get('district')
                            # county = c.get('county')
                            sub_county = c.get('sub_county')
                            parish = c.get('parish')
                            village = c.get('village')
                            contact_person = c.get('contact_person')
                            phone_number = c.get('phone_number')

                            if district:
                                dl = [dist for dist in District.objects.filter(name=district)]
                                do = dl[0] if len(dl) > 0 else None

                            # if county:
                            #     cl = [c for c in
                            #            County.objects.filter(district__name=district, name=county)]
                            #     co = cl[0] if len(cl) > 0 else None

                            if sub_county:
                                scl = [subc for subc in
                                       SubCounty.objects.filter(county__district__name=district, name=sub_county)]
                                sco = scl[0] if len(scl) > 0 else None

                            if parish:
                                pl = [p for p in
                                       Parish.objects.filter(sub_county__name=sub_county, name=parish)]
                                po = pl[0] if len(pl) > 0 else None

                            if not FarmerGroup.objects.filter(name=name, sub_county=sco, village=village).exists():
                                code = self.check_code(name)
                                FarmerGroup(
                                    # partner=partner,
                                    name=name,
                                    code=code,
                                    district=do,
                                    # county=co,
                                    sub_county=sco,
                                    parish=po,
                                    village=village,
                                    contact_person_name=contact_person,
                                    phone_number=phone_number,
                                    created_by=self.request.user
                                ).save()

                        return redirect('coop:fg_list')
                    except Exception as err:
                        log_error()
                        print(err)
                        data['error'] = err

        data['form'] = form
        data['active'] = ['_farmer_group']
        return render(request, self.template_name, data)

    def check_code(self, name):
        cnt = FarmerGroup.objects.all().count()
        code = "{}{}{}".format(get_consontant_upper(name), cnt+1, generate_numeric(3))
        print(code)
        q = FarmerGroup.objects.filter(code=code)
        if q.exists():
            count = q.count()
            q2 = FarmerGroup.objects.filter(code__contains=name.upper()[:3])
            code = "%s%s" % (name.upper()[:3], generate_numeric(size=2))
            return code
        return code