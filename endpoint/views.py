# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import datetime
import string
import random
import traceback
from django.shortcuts import render
from django.db import transaction
from django.db.models import Q, Value
from django.db.models.functions import Concat

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FileUploadParser
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser, FileUploadParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token

from django.forms.models import model_to_dict
from django.contrib.auth import authenticate

from userprofile.models import Profile
from product.models import ProductVariation, ProductVariationPrice
from conf.models import District, County, SubCounty, Village
from coop.models import Cooperative, CooperativeMember, Collection, OKOMemberPolicy
from activity.models import ThematicArea, TrainingModule, TrainingAttendance, TrainingContent
from endpoint.serializers import *

from coop.views.member import save_transaction
from conf.utils import generate_numeric, generate_alpanumeric, genetate_uuid4, log_error, get_message_template as message_template
from coop.utils import sendMemberSMS
from api.Mobis import Mobis
from api.OKOTransactions import OKOTransaction


class Login(APIView):

    def post(self, request, format=None):
        serializer = LoginSerializer(data=request.data)
        try:
            if serializer.is_valid():
                data = request.data
                cooperative = False
                username = data.get('username')
                password = data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                #if hasattr(user.profile.access_level, 'name'):
                #if user.profile.access_level.name.lower()  == "cooperative" and user.cooperative_admin:
                #    cooperative = True
                #if cooperative:
                    q_token = Token.objects.filter(user=user)
                    if q_token.exists():
                        
                        token = q_token[0]
                        qs = Profile.objects.get(user=user)
                        product = Product.objects.values('name').all()
                        cooperatives = [{"id": c.id, "name": c.name, "code": c.code} for c in Cooperative.objects.all().order_by('name')]
                        members = CooperativeMember.objects.all().order_by('-surname')
                        variation = ProductVariation.objects.values('id', 'product', 'name').all()
                        variation_price = ProductVariationPrice.objects.values('id', 'product', 'product__name', 'price').all()
                        district = District.objects.values('id', 'name').all()
                        county = County.objects.values('id', 'district', 'name').all()
                        sub_county = SubCounty.objects.values('id', 'county', 'name').all()
                        thematic_area = ThematicArea.objects.values('id', 'thematic_area').all()
                        content = TrainingContent.objects.values('id', 'thematic_area', 'sequence', 'topic', 'content').all()
                        user_type = user.profile.access_level.name.upper() if user.profile.access_level else "NONE"
                        is_admin = user.is_superuser
                        cooperative = None
                        if hasattr(user.profile.access_level, 'name'):
                            if user.profile.access_level == "COOPERATIVE":
                                if user.cooperative_admin:
                                    members = members.filter(cooperative=cooperative)
                                    cooperative = {"name": user.cooperative_admin.cooperative.name,
                                                   "id": user.cooperative_admin.cooperative.id,
						   "code": user.cooperative_admin.cooperative.code}
                        return Response({
                            "status": "OK",
                            "token": token.key,
                            
                            "user": {"username": qs.user.username, "id": qs.user.id, "user_type": user_type, "is_admin": is_admin},
                            "cooperative": cooperative,
                            "cooperatives": cooperatives,
                            "product": product,
                            "variation": variation,
                            "variation_price": variation_price,
                            "district": district,
                            "county": county,
                            "members": [],#MemberListSerializer(members, many=True).data,
                            "sub_county": sub_county,
                            "thematic_area": thematic_area,
                            "content": content,
                            "response": "Login success"
                            }, status.HTTP_200_OK)
                    return Response({"status": "ERROR", "response": "Access Denied"}, status.HTTP_200_OK)
                        
                return Response({"status": "ERROR", "response": "Invalid Username or Password"}, status.HTTP_200_OK)
        except Exception as err:
            return Response({"status": "ERROR", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentValidateView(APIView):

    def post(self, request, format=None):
        phone_number = request.data.get('phone_number')
        agent_code = request.data.get('agent_code')
        profiles = Profile.objects.filter(msisdn=phone_number)

        if profiles.exists():
            profile = profiles[0]
            q_token = Token.objects.filter(user=profile.user)
            if q_token.exists():
                cooperatives = [{"id": c.cooperative.id, "name": c.cooperative.name, "code": c.cooperative.code} for c
                                in
                                OtherCooperativeAdmin.objects.filter(user=profile.user)]

                token = q_token[0]
                return Response({"status": "OK", "response": {"token": token.key, "cooperatives": cooperatives }}, status.HTTP_200_OK)
        return Response({"status": "ERROR", "response": "Agent not Found"}, status.HTTP_200_OK)


class MemberEndpoint(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = [FormParser, MultiPartParser, FileUploadParser]
    
    def post(self, request, format=None):
        if request.data.get('id_number') == '':
            request.data['id_number'] = None
        member = MemberSerializer(data=request.data)
        mem = CooperativeMember.objects.filter(member_id=request.data.get('member_id'))
        if mem.count() < 1:
            mem = CooperativeMember.objects.filter(first_name=request.data.get('first_name'),other_name=request.data.get('other_name'),surname=request.data.get('surname'),date_of_birth=request.data.get('date_of_birth'))
        print ("ADDING........%s, %s " % (mem.count(), request.data.get('member_id')))

        if mem.count() > 0:
            member = MemberSerializer(mem[0], data=request.data) 
        try:
            if member.is_valid():
                
                with transaction.atomic():

                    if mem.count() < 1: 
                        __member = member.save()
                        __member.member_id = self.generate_member_id()
                        __member.create_by = request.user
                        __member.save()
                        params = {
                            "branch_id": __member.cooperative.trust_network_id,
                            "title": "",
                            "first_name": __member.first_name,
                            "surname": __member.surname,
                            "other_name": None,
                            "date_of_birth": __member.date_of_birth.strftime("%Y-%m-%d"),
                            "gender": __member.gender,
                            "phone_number": __member.phone_number,
                            "mobile_money_num": None,
                            "parish": __member.village,
                            "district": __member.district.name,
                            "country": "Uganda",
                            "kin_full_name": __member.surname,
                            "kin_phone_number": __member.phone_number,
                            "registration_date": __member.create_date.strftime("%Y-%m-%d"),
                            "member_id": __member.member_id,
                            "is_subscribed_sms": "0"
                        }

                        if __member.cooperative.mobis_slug:
                            mobis = Mobis(__member.cooperative.mobis_slug, __member.cooperative.mobis_username, self.object.cooperative.mobis_password)
                            mobis_response = mobis.create_individual(params)
                            print(mobis_response)
                            if not mobis_response.get("error"):
                                __member.ensuubuko_customer_id = mobis_response.get("data").get("id")
                                __member.ensuubuko_id = mobis_response.get("data").get("customer_number")
                                __member.ensuubuko_info = mobis_response
                                __member.save()
                        mes = message_template()
                        if mes:
                            message = message_template().member_registration
                            if re.search('<NAME>', message):
                                if __member.surname:
                                    message = message.replace('<NAME>', '%s %s' % (__member.surname.title(), __member.first_name.title()))
                                    message = message.replace('<COOPERATIVE>', __member.cooperative.name)
                                    message = message.replace('<IDNUMBER>', __member.member_id)
                                    sendMemberSMS(request, __member, message)
                    else:
                        print("UPDATING..")
                        __member = mem[0]
                        CooperativeMember.objects.filter(member_id=request.data.get('member_id')).update(
                        image=request.data.get("image"),
                        surname=request.data.get("surname"),
                        first_name=request.data.get("first_name"),
                        other_name=request.data.get("other_name"),
                        id_number=request.data.get("id_number"),
                        date_of_birth=request.data.get("date_of_birth"),
                        gender=request.data.get("gender"),
                        maritual_status=request.data.get("maritual_status"),
                        phone_number=request.data.get("phone_number"), 
                        email=request.data.get("email"), 
                        district=request.data.get("district"), 
                        county=request.data.get("county"), 
                        sub_county=request.data.get("sub_county"), 
                        village=request.data.get("village"),
                        coop_role=request.data.get("coop_role"),
                        land_acreage=request.data.get("land_acreage"),
                        product=request.data.get("product")
                        )
                    return Response(
                        {"status": "OK", "response": "Farmer Profile Saved Successfully", "member_id": __member.member_id},
                        status.HTTP_200_OK)
            return Response(member.errors)
        except Exception as err:
            print(traceback.format_exc())
            log_error()
            return Response({"status": "ERROR", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(member.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def safe_get(self, _model, _value):
        try:
            return get_object_or_404(_model, cooperative_member=_value)
        except Exception:
            return None
    
    def generate_member_id(self):
        member = CooperativeMember.objects.all()
        rnd = generate_numeric(prefix="", size=3)
        count = "%s%s" % (rnd, member.count() + 1)
        
        today = datetime.today()
        datem = today.year
        yr = str(datem)[2:]
        # idno = generate_numeric(size=4, prefix=str(m.cooperative.code)+yr)
        # fint = "%04d"%count
        # idno = str(cooperative.code)+yr+fint
        # member = member.filter(member_id=idno)
        idno = self.check_id(member, int(count), yr)
        return idno
    
    def check_id(self, member, count, yr):
        fint = "%04d"%count
        idno = yr+fint
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            print "iteration count %s" % count
            return self.check_id(member, count, yr)
        return idno


class USSDMemberEndpoint(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        member = MemberSerializer(data=request.data)
        farmer_name = "%s %s %s" % (request.data.get('first_name'), request.data.get('surname'), request.data.get('other_name'))
        mem = CooperativeMember.objects.annotate(farmer_name=Concat('first_name', Value(' '), 'surname', Value(' '), 'other_name')).filter(Q(farmer_name=farmer_name)| Q(phone_number=request.data.get("phone_number")))
        print("ADDING........%s, %s " % (mem.count(), request.data))
        if mem.count() > 0:
            member = MemberSerializer(mem[0], data=request.data)
        try:
            if member.is_valid():

                with transaction.atomic():
                    if mem.count() < 1:
                        __member = member.save()
                        __member.member_id = self.generate_member_id(__member.cooperative)
                        __member.create_by = request.user
                        __member.save()
                        mes = message_template()
                        if mes:
                            message = message_template().member_registration
                            if re.search('<NAME>', message):
                                if __member.surname:
                                    message = message.replace('<NAME>', '%s %s' % (
                                    __member.surname.title(), __member.first_name.title()))
                                    message = message.replace('<COOPERATIVE>', __member.cooperative.name)
                                    message = message.replace('<IDNUMBER>', __member.member_id)
                                    sendMemberSMS(request, __member, message)
                    else:
                        print("UPDATING..")
                        __member = mem[0]
                        CooperativeMember.objects.filter(member_id=request.data.get('member_id')).update(
                            image=request.data.get("image"),
                            surname=request.data.get("surname"),
                            first_name=request.data.get("first_name"),
                            other_name=request.data.get("other_name"),
                            date_of_birth=request.data.get("date_of_birth"),
                            gender=request.data.get("gender"),
                            maritual_status=request.data.get("maritual_status"),
                            phone_number=request.data.get("phone_number"),
                            email=request.data.get("email"),
                            district=request.data.get("district"),
                            county=request.data.get("county"),
                            sub_county=request.data.get("sub_county"),
                            village=request.data.get("village"),
                            coop_role=request.data.get("coop_role"),
                            land_acreage=request.data.get("land_acreage"),
                            product=request.data.get("product"),
                            is_refugee=request.data.get("is_refugee"),
                            seed_multiplier=request.data.get("seed_multiplier"),
                        )
                    return Response(
                        {"status": "OK", "response": "Farmer Profile Saved Successfully",
                         "member_id": __member.member_id},
                        status.HTTP_200_OK)
            return Response(member.errors)
        except Exception as err:
            return Response({"status": "ERROR", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(member.errors, status=status.HTTP_400_BAD_REQUEST)

    def safe_get(self, _model, _value):
        try:
            return get_object_or_404(_model, cooperative_member=_value)
        except Exception:
            return None

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
        fint = "%04d" % count
        idno = str(cooperative.code) + yr + fint
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            print
            "iteration count %s" % count
            return self.check_id(member, cooperative, count, yr)
        return idno


class CooperativeListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, member=None, format=None):
        cooperatives = Cooperative.objects.all()
        serializer = CooperativeSerializer(cooperatives, many=True)
        return Response(serializer.data)

    
class MemberList(APIView):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, member=None, format=None):
        cooperative = request.data.get('cooperative')  
        # members = CooperativeMember.objects.filter(cooperative=request.user.cooperative_admin.cooperative).order_by('-surname')
        if cooperative == 'all':
            members = CooperativeMember.objects.all().order_by('-surname')
        else:
            members = CooperativeMember.objects.filter(cooperative=cooperative).order_by('-surname')
        if member:
            members = members.filter(Q(member_id=member)|Q(phone_number=member)|Q(other_phone_number=member))
        serializer = MemberListSerializer(members, many=True)
        return Response(serializer.data)
    

class TrainingSessionView(APIView):
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        pk = request.data.get('session_id')
        print pk
        training = TrainingSessionSerializer(data=request.data)
        
        try:
            if pk:
                ts = TrainingSession.objects.get(pk=pk)
                print ts
                training = TrainingSessionUpdateSerializer(ts, data=request.data)
            print request.data
            if training.is_valid():
                print training
                with transaction.atomic():
                    ta = request.data.get('thematic_area')
                    tq = ThematicArea.objects.filter(pk=ta)
                    __training = training.save(thematic_area=tq[0])
                    __training.trainer = request.user
                    __training.created_by = request.user
                    if not pk:
                        __training.training_reference = generate_alpanumeric(prefix="TR", size=8)
                    __training.save()
                    
                    #get Member list
                    data = request.data
                    if pk:
                        __training.coop_member.clear()
                    for m in data.get('member'):
                        member = CooperativeMember.objects.get(member_id=m)
                        __training.coop_member.add(member)
                    
                    return Response(
                        {"status": "OK", "response": "Training Session Saved"},
                        status.HTTP_200_OK)
            
            return Response(training.errors)
        except Exception as err:
            log_error()
            return Response({"status": "ERRORf", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(training.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class TrainingSessionListView(APIView):
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        cooperative = request.data.get('cooperative')
        print "Cooperative" + cooperative
        training = TrainingSession.objects.filter(cooperative=cooperative).order_by('-create_date')
        # training = TrainingSession.objects.all().order_by('-create_date')
        serializer = TrainingSessionSerializer(training, many=True)
        return Response(serializer.data)
    

class TrainingSessionEditView(APIView): #DRY thrown out here. Need fix
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, session, format=None):
        cooperative = request.data.get('cooperative')
        print "Cooperative" + cooperative
        training = TrainingSession.objects.filter(cooperative=cooperative, pk=session).order_by('-create_date')
        # training = TrainingSession.objects.all().order_by('-create_date')
        serializer = TrainingSessionEditSerializer(training, many=True)
        return Response(serializer.data)
    
    
class CollectionCreateView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        collection = CollectionSerializer(data=request.data)
        if collection.is_valid():
            try:
                with transaction.atomic():
                    c = collection.save(created_by = request.user)
                    # collection_date = data.get('collection_date')
                    # is_member = data.get('is_member')
                    # member = data.get('member')
                    # name = data.get('name')
                    # phone_number = data.get('phone_number')
                    # collection_reference = data.get('collection_reference')
                    # product = data.get('product')
                    # quantity = data.get('quantity')
                    # unit_price = data.get('unit_price')
                    # total_price = data.get('total_price')
                    # created_by = data.get('created_by')
                    if c.is_member:
                        params = {
                            'amount': c.total_price,
                            'member': c.member,
                            'transaction_reference': c.collection_reference ,
                            'transaction_type': 'COLLECTION',
                            'entry_type': 'CREDIT'
                        }
                        member = CooperativeMember.objects.filter(pk=c.member.id)
                        if member.exists():
                            member = member[0]
                            qty_bal = member.collection_quantity if member.collection_quantity else 0
                            new_bal = c.quantity + qty_bal
                            member.collection_quantity = new_bal
                            member.save()
                        save_transaction(params)
                        try:
                            message = message_template().collection
                            message = message.replace('<NAME>', member.surname)
                            message = message.replace('<QTY>', "%s%s" % (c.quantity, c.product.unit.code))
                            message = message.replace('<PRODUCT>', "%s" % (c.product.name))
                            message = message.replace('<COOP>', c.cooperative.name)
                            message = message.replace('<DATE>', c.collection_date.strftime('%Y-%m-%d'))
                            message = message.replace('<AMOUNT>', "%s" % c.total_price)
                            message = message.replace('<REFNO>', c.collection_reference)
                            sendMemberSMS(self.request, member, message)
                        except Exception:
                            log_error()

                    return Response(
                                {"status": "OK", "response": "Collection Saved."},
                                status.HTTP_200_OK)
            except Exception as e:
                log_error()
                return Response({"status": "ERROR", "response": "error"}, status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(collection.errors)
            

class CollectionListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        #raise Exception(request.user)
        cooperative = request.data.get('cooperative')
        collections = Collection.objects.filter(cooperative=cooperative).order_by('-create_date')
        serializer = CollectionListSerializer(collections, many=True)
        return Response(serializer.data)
    

class MemberOrderListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        cooperative = request.data.get('cooperative')
        orders = MemberOrder.objects.filter(cooperative=cooperative).order_by('-create_date')
        serializer = MemberOrderSerializer(orders, many=True)
        return Response(serializer.data)


class OrderItemListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, order, format=None):
        order_items = OrderItem.objects.filter(order=order).order_by('-create_date')
        serializer = OrderItemSerializer(order_items, many=True)
        return Response(serializer.data)


class ItemView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        items = Item.objects.all()
        serializer = ItemSerializer(items, many=True)
        return Response(serializer.data)
    
    
class OrderCreateView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        data = request.data 
        mo = MemberOrderFormSerializer(data=data)
        if mo.is_valid():
            _order = mo.save(created_by=request.user)
            for i in data.get("item"):
                oi = OrderItemSerializer_(data=i)
                if oi.is_valid():
                    oi.save(order=_order, created_by=request.user)
                else:
                    return Response(oi.errors)
            return Response({"status": "OK", "response": "Order Saved"}, status.HTTP_200_OK)
        return Response(mo.errors)


class UserList(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        data = request.data
        users = Profile.objects.all()
        serializer = AgentSerializer(users, context={'request': request}, many=True)
        return Response(serializer.data)


class OKOInsuranceView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        data = request.data

        member_id = data.get('member_id')
        print(data)

        if member_id:
            member = CooperativeMember.objects.get(member_id=member_id)
            payload = {
                "district": {
                    "name": member.district.name if member.district else ""
                },
                "county": "",
                "sub_county": member.sub_county.name if member.sub_county else "",
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

                # if "policyId" in res and res.get('policyId'):
                #     policyId = res.get('policyId')
                #     amountDue = res.get('amountDue')
            #
            #         qs = OKOMemberPolicy.objects.filter(policyId=policyId)
            #         if qs.exists():
            #             qs = qs[0]
            #             qs.amount_due = amountDue
            #             qs.save()
            #         else:
            #             OKOMemberPolicy.objects.create(
            #                 cooperative_member=member,
            #                 policyId=policyId,
            #                 amount_due=amountDue,
            #                 created_by=request.user
            #             )
            #         return Response({"status": "OK", "response": "Policy Created Successfully. Policy ID: %s" % policyId }, status.HTTP_200_OK)
                return Response({"status": "OK", "response": "Success"}, status.HTTP_200_OK)
            except Exception as e:
                log_error()
                return Response({"status": "ERROR", "response": e}, status.HTTP_200_OK)


        return Response({"status": "ERROR", "response": "Member ID '%s' not Found" % member_id}, status.HTTP_200_OK)

