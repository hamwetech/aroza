# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.db.models import Sum
from django.views.generic import TemplateView
from django.db.models import Q, CharField, Max, Sum, Count, Value as V
from django.db.models.functions import Concat
from coop.models import *
from activity.models import *
from payment.models import *
from credit.models import *
from userprofile.models import Profile
from product.models import ProductVariationPrice, Supplier
from messaging.models import OutgoingMessages


class DashboardView(TemplateView):
    template_name = "dashboard.html"
    
    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        cooperatives = Cooperative.objects.all()
        members = CooperativeMember.objects.all()
        suppliers = Supplier.objects.all()
        orders = MemberOrder.objects.all()
        loans = LoanRequest.objects.all()
        sum_loans = loans.filter(status='APPROVED').aggregate(sum=Sum('requested_amount'))
        agents = Profile.objects.filter(access_level__name='AGENT')
        district_summary = members.values('district__name').annotate(dc=Count('id'))

        cooperative_contribution = CooperativeContribution.objects.all().order_by('-update_date')[:5]
        cooperative_shares = CooperativeShareTransaction.objects.all().order_by('-update_date')
        product_price = ProductVariationPrice.objects.all().order_by('-update_date')
        collections = Collection.objects.all().order_by('-update_date')
        payments = MemberPaymentTransaction.objects.all().order_by('-transaction_date')
        success_payments = payments.filter(status='SUCCESSFUL')
        training = TrainingSession.objects.all().order_by('-create_date')
        # supply_requests = MemberSupplyRequest.objects.all().order_by('-create_date')
        # supply_requests = supply_requests.filter(status='ACCEPTED')
        m_shares = CooperativeMemberSharesLog.objects
        messages = OutgoingMessages.objects.all()
        if not self.request.user.profile.is_union():
            if hasattr(self.request.user, 'cooperative_admin'):

                coop_admin = self.request.user.cooperative_admin.cooperative
                cooperatives = cooperatives.filter(pk=coop_admin.id)
                members = members.filter(cooperative = coop_admin)
                cooperative_shares = cooperative_shares.filter(cooperative = coop_admin)
                m_shares = m_shares.filter(cooperative_member__cooperative = coop_admin)
                collections = collections.filter(member__cooperative = coop_admin)
                district_summary = district_summary.filter(cooperative = coop_admin)
        collection_qty = collections.aggregate(total_amount=Sum('quantity'))
        total_payment = success_payments.aggregate(total_amount=Sum('amount'))
        collection_amt = collections.aggregate(total_amount=Sum('total_price'))
        members_shares = members.aggregate(total_amount=Sum('shares'))
        male = members.filter(Q(gender='male') | Q(gender='m'))
        female = members.filter(Q(gender='female') | Q(gender='f'))
        is_refugee = members.filter(is_refugee=True)
        is_handicap = members.filter(is_handicap=True)
        teeyouthmale = [m for m in male if m.age <= 29]
        teeyouthf = [f for f in female if f.age <= 29]
        adultmale = [m.age for m in male if m.age >= 30]
        adultfemale = [f for f in female if f.age >= 30]


        # members_animals = members.aggregate(total_amount=Sum('animal_count'))
        shares = cooperatives.aggregate(total_amount=Sum('shares'))
        m_shares = m_shares.values('cooperative_member',
                                   name=Concat('cooperative_member__surname',
                                               V(' '),
                                               'cooperative_member__first_name'
                                               ),
                                   
                                   ).annotate(total_amount=Sum('amount'), total_shares=Sum('shares'), transaction_date=Max('transaction_date')).order_by('-transaction_date')
        
        cooperative_shares = cooperative_shares.values('cooperative',
                                   'cooperative__name',
                                   ).annotate(total_amount=Sum('amount_paid'), total_shares=Sum('shares_bought'), transaction_date=Max('transaction_date')).order_by('-transaction_date')
        
        context['cooperatives'] = cooperatives.count()
        context['suppliers'] = suppliers.count()
        context['orders'] = orders.count()
        context['loans'] = loans.count()
        context['agents'] = agents.count()
        context['sum_loans'] = sum_loans
        context['coop_summary'] = cooperatives
        context['district_summary'] = district_summary

        context['shares'] = shares['total_amount']
        context['transactions'] = Cooperative.objects.all().count()
        context['members'] = members.count()
        context['male'] = male.count()
        context['female'] = female.count()
        context['is_refugee'] = is_refugee.count()
        context['is_handicap'] = is_handicap.count()

        context['teeyouthmale'] = len(teeyouthmale)
        context['teeyouthf'] = len(teeyouthf)
        context['adultmale'] = len(adultmale)
        context['adultfemale'] = len(adultfemale)

        context['active'] = ['_dashboard', '']
        context['members_shares'] = members_shares['total_amount']
        context['m_shares'] = m_shares[:5]
        context['collections_latest'] = collections[:5]
        context['collections'] = collection_qty['total_amount']
        context['collection_amt'] = collection_amt['total_amount']
        context['total_payment'] = total_payment['total_amount']
        
        context['cooperative_contribution'] = cooperative_contribution
        context['cooperative_shares'] = cooperative_shares[:5]
        context['training'] = training[:5]
        context['product_price'] = product_price
        context['sms'] = messages.filter(status='SENT').count()
        # context['supply_requests'] = supply_requests[:5]
        return context
    
    


