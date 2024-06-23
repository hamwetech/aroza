from __future__ import unicode_literals
import json
import xlrd
import xlwt
import datetime
from django.db import transaction
from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse_lazy
from django.forms.formsets import formset_factory, BaseFormSet
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView

from credit.models import LoanRequest, CreditManager
from credit.utils import create_loan_transaction
from coop.models import MemberOrder, CooperativeMember, OrderItem
from coop.forms import OrderItemForm, MemberOrderForm, OrderPaymentForm, OrderSearchForm
from coop.views.member import save_transaction
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, log_debug, generate_numeric, float_to_intstring, get_deleted_objects,\
get_message_template as message_template
from credit.RawFinancialAPI import RawFinancial

class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        
        context.update(self.extra_context)
        return context
    
    
class MemberOrderListView(ExtraContext, ListView):
    model = MemberOrder
    ordering = ['-create_date']
    extra_context = {'active': ['_order']}
    
    def get_queryset(self):
        queryset = super(MemberOrderListView, self).get_queryset()
        
        if self.request.user.profile.is_cooperative():
            if not self.request.user.is_superuser:
                cooperative = self.request.user.cooperative_admin.cooperative
                queryset = queryset.filter(member__cooperative=cooperative)

        if self.request.user.profile.is_supplier():
            if not self.request.user.is_superuser:
                supplier = self.request.user.supplier_admin.supplier
                order_item = OrderItem.objects.filter(item__supplier=supplier)
                o = []
                for oi in order_item:
                    o.append(oi.order)
                queryset = queryset.filter(get_supplier_orders=supplier)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(MemberOrderListView, self).get_context_data(**kwargs)
        return context


class MemberOrderCreateView(View):
    template_name = 'coop/order_item_form.html'
    
    def get(self, request, *args, **kwargs):
        
        pk = self.kwargs.get('pk')
        prod = None
        var = None
        initial = None
        extra=1
       
        form = MemberOrderForm(request=request)
        order_form = formset_factory(OrderItemForm, formset=BaseFormSet, extra=extra)
        order_formset = order_form(prefix='order', initial=initial)
        data = {
            'order_formset': order_formset,
            'form': form,
            'active': ['_order'],
        }
        return render(request, self.template_name, data)
    
    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        prod = None
        var = None
        initial = None
        extra=1
        form = MemberOrderForm(request.POST, request=request)
        order_form = formset_factory(OrderItemForm, formset=BaseFormSet, extra=extra)
        order_formset = order_form(request.POST, prefix='order', initial=initial)
        try:
            with transaction.atomic():
                if form.is_valid() and order_formset.is_valid():
                    mo = form.save(commit=False)
                    mo.order_reference = generate_numeric(8, '30')
                    mo.created_by = request.user
                    mo.save()
                    price = 0
                    for orderi in order_formset:
                        os = orderi.save(commit=False)
                        os.order = mo
                        os.unit_price = os.item.price
                        os.created_by = request.user
                        os.save()
                        price += os.price
                    mo.order_price = price
                    mo.save()
                    return redirect('coop:order_list')
        except Exception as e:
            log_error()
        data = {
            'order_formset': order_formset,
            'form': form,
            'active': ['_order'],
        }
        return render(request, self.template_name, data)


class MemberOrderDetailView(ExtraContext, DetailView):
    model = MemberOrder
    extra_context = {'active': ['_order']}


class MemberOrderItemListView(ExtraContext, ListView):
    model = OrderItem
    ordering = ['-create_date']
    extra_context = {'active': ['_order']}

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(MemberOrderItemListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(MemberOrderItemListView, self).get_queryset()

        if self.request.user.profile.is_cooperative():
            if not self.request.user.is_superuser:
                cooperative = self.request.user.cooperative_admin.cooperative
                queryset = queryset.filter(order__member__cooperative=cooperative)

        if self.request.user.profile.is_supplier():
            if not self.request.user.is_superuser:
                supplier = self.request.user.supplier_admin.supplier
                queryset = queryset.filter(item__supplier=supplier).exclude(status__in=['PENDING', 'CONFIRMED'])
        return queryset


    def download_file(self, *args, **kwargs):

        _value = []
        columns = []
        member = self.request.GET.get('member')
        coop = self.request.GET.get('cooperative')
        status = self.request.GET.get('status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        profile_choices = ['order__order_reference', 'order__cooperative__name', 'order__member__surname', 'order__member__first_name',
                           'order__member__gender', 'order__member__date_of_birth', 'order__member__district__name',
                           'item__name', 'quantity', 'unit_price', 'price', 'status', 'order__order_date', 'order__created_by__username']

        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
        # Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')

        # The response also has additional Content-Disposition header, which contains
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=MemberOrders_%s.xls' % datetime.datetime.now().strftime(
            '%Y%m%d%H%M%S')

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

        _members = OrderItem.objects.values(*profile_choices).all()


        if coop:
            _members = _members.filter(cooperative__id=coop)
        if member:
            _members = _members.filter(member__id=member)
        if status:
            _members = _members.filter(status=status)
        if start_date:
            _members = _members.filter(order_date__gte=start_date)
        if end_date:
            _members = _members.filter(order_date__lte=end_date)

        for m in _members:

            row_num += 1
            ##print profile_choices
            row = [
                m['%s' % x] if 'order_date' not in x else m['%s' % x].strftime('%d-%m-%Y') if m.get('%s' % x) else ""
                for x in profile_choices]

            for col_num in range(len(row)):
                worksheet.write(row_num, col_num, row[col_num])
        workbook.save(response)
        return response

    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces:
            # Check if string is in the main string
            if elem in mainString:
                # Replace the string
                mainString = mainString.replace(elem, newString)

        return mainString


class MemberOrderDeleteView(ExtraContext, DeleteView):
    model = MemberOrder
    extra_context = {'active': ['_order']}
    success_url = reverse_lazy('coop:order_list')
    
    def get_context_data(self, **kwargs):
        #
        context = super(MemberOrderDeleteView, self).get_context_data(**kwargs)
        #
        
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects']=deletable_objects
        context['model_count']=dict(model_count).items()
        context['protected']=protected
        #
        return context
    

class MemberOrderStatusView(View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        status = self.kwargs.get('status')
        today = datetime.datetime.today()
        try:
            mo = MemberOrder.objects.get(pk=pk)
            if status == 'ACCEPT':
                mo.accept_date = today

            if status == 'SHIP':
                mo.ship_date = today
            if status == 'DELIVERED':
                mo.delivery_date = today
            if status == 'ACCEPT_DELIVERY':
                mo.delivery_accept_date = today
            if status == 'REJECT_DELIVERY':
                mo.delivery_reject_date = today
            if status == 'COLLECTED':
                mo.collect_date = today
            mo.status = status
            mo.save()
        except Exception as e:
            log_error()
        
        return redirect('coop:order_list')


class OrderItemStatusView(View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        status = self.kwargs.get('status')
        today = datetime.datetime.today()
        mm = None
        try:
            mo = OrderItem.objects.get(pk=pk)
            mm = MemberOrder.objects.get(pk=mo.order.id)
            if status == 'CONFIRMED':
                mo.confirm_date = today
                mm.status = 'PROCESSING'
                mm.save()
            #     If Loan Create Request
                if mm.request_type == "LOAN":
                    today = datetime.datetime.now()
                    lrq = LoanRequest.objects.filter(create_date__year=today.strftime("%Y"))
                    ln_cnt = lrq.count() + 1
                    reference = "LRQ/%s/%s" % (today.strftime("%y"), format(ln_cnt, '04'))
                    lro = LoanRequest.objects.create(
                        reference = reference,
                        member=mm.member,
                        credit_manager=CreditManager.objects.all()[0],
                        requested_amount =mo.price,
                        order_item=mo,
                        request_date=datetime.datetime.now()
                    )
            #         RAW Financial API
                    rf = RawFinancial()
                    borrower_id = genetate_uuid4()
                    print("klsklksdlklskd============================")
                    if mm.member.borrower_id:
                        borrower_id = mm.member.borrower_id
                    if not mm.member.borrower_id:
                        params = {
                            "borrower_id": borrower_id,
                            "trust_network": mm.member.cooperative.trust_network_id,
                            "first_name": mm.member.first_name,
                            "last_name": mm.member.surname,
                            "phone_number": mm.member.phone_number,
                            "nin": mm.member.id_number,
                            "email": "",
                            "address": "",
                        }
                        regr = rf.register_borrower(params)
                        print("=======================")
                        print(regr)
                        if "success" in regr:
                            print("saved...")
                            mm.member.borrower_id = borrower_id
                            mm.member.save()

                    params_loan = {
                        "channel_borrower_uid": borrower_id,
                        "loan_amount": mo.price,
                        "loan_purpose": "%s" % mo,
                        "loan_duration": 90,
                    }
                    lr = rf.loan_request(params_loan)
                    lro.response = lr
                    if "succes" in lr:
                        print("loan created...")
                        lro.loan_request_id = lr['loan_request_id']
                    else:
                        lro.status = "FAILED"
                        mo.confirm_date = None
                        status = "PENDING"
                    lro.save()
            #        to do send email to credit management email
            if status == 'APPROVED':
                mo.approve_date = today
            if status == 'PROCESSING':
                mo.processing_start_date = today
            if status == 'SHIP':
                mo.ship_date = today
            if status == 'DELIVERED':
                mo.delivery_date = today
            if status == 'ACCEPT_DELIVERY':
                mo.delivery_accept_date = today

            if status == 'REJECT_DELIVERY':
                mo.delivery_reject_date = today
            if status == 'COLLECTED':
                mo.collect_date = today
            mo.status = status
            mo.save()
            self.update_order(mm)
        except Exception as e:
            print(e)
            log_error()
        if request.user.profile.is_supplier():
            return redirect('coop:order_item_list')
        return redirect('coop:order_detail', pk=mm.id)

    def update_order(self, order):
        mo = OrderItem.objects.filter(order=order)
        pending_items = []
        for item in mo:
            if item.status != "ACCEPT_DELIVERY":
                pending_items.append(item.id)

        if len(pending_items) == 0:
            order.status = "COMPLETED"
            order.save()


class OrderPaymentView(FormView):
    form_class = OrderPaymentForm
    template_name = "coop/payment_form.html"
    success_url = reverse_lazy("coop:order_list")

    def get_context_data(self, *args, **kwargs):
        context = super(OrderPaymentView, self).get_context_data(*args, **kwargs)
        context['object'] = MemberOrder.objects.get(pk=self.kwargs.get('pk'))
        return context


class OrderItemListView(ExtraContext, ListView):
    model = OrderItem
    template_name = "core/memberorder_item.html"
    ordering = ['-create_date']
    extra_context = {'active': ['_order']}

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(OrderItemListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(OrderItemListView, self).get_queryset()

        if not self.request.user.profile.is_union():
            if not self.request.user.profile.is_partner():
                cooperative = self.request.user.cooperative_admin.cooperative
                queryset = queryset.filter(member__cooperative=cooperative)
        member = self.request.GET.get('member')
        cooperative = self.request.GET.get('cooperative')
        status = self.request.GET.get('status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if member:
            queryset = queryset.filter(member=member)
        if cooperative:
            queryset = queryset.filter(cooperative=cooperative)
        if status:
            queryset = queryset.filter(status=status)
        if start_date:
            queryset = queryset.filter(order_date__gte=start_date)
            print(start_date)
            print(queryset.query)
        if end_date:
            queryset = queryset.filter(order_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super(OrderItemListView, self).get_context_data(**kwargs)
        context['form'] = OrderSearchForm(self.request.GET)
        return context

    def download_file(self, *args, **kwargs):

        _value = []
        columns = []
        member = self.request.GET.get('member')
        coop = self.request.GET.get('cooperative')
        status = self.request.GET.get('status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        profile_choices = ['order__order_reference', 'order__cooperative__name', 'order__member__surname', 'order__member__first_name',
                           'item__name', 'quantity', 'unit_price', 'price', 'order__order_date', 'order__created_by__username']

        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
        # Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')

        # The response also has additional Content-Disposition header, which contains
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=MemberOrders_%s.xls' % datetime.datetime.now().strftime(
            '%Y%m%d%H%M%S')

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

        _members = OrderItem.objects.values(*profile_choices).all()


        if coop:
            _members = _members.filter(cooperative__id=coop)
        if member:
            _members = _members.filter(member__id=member)
        if status:
            _members = _members.filter(status=status)
        if start_date:
            _members = _members.filter(order_date__gte=start_date)
        if end_date:
            _members = _members.filter(order_date__lte=end_date)

        for m in _members:

            row_num += 1
            ##print profile_choices
            row = [
                m['%s' % x] if 'order_date' not in x else m['%s' % x].strftime('%d-%m-%Y') if m.get('%s' % x) else ""
                for x in profile_choices]

            for col_num in range(len(row)):
                worksheet.write(row_num, col_num, row[col_num])
        workbook.save(response)
        return response

    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces:
            # Check if string is in the main string
            if elem in mainString:
                # Replace the string
                mainString = mainString.replace(elem, newString)

        return mainString
