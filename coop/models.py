# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import qrcode
import StringIO
import calendar
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models import F, Sum, Q
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile

from account.models import Account
from conf.models import District, County, SubCounty, Village, Parish, PaymentMethod
from product.models import Product, ProductVariation, ProductUnit, Item
# from partner.models import PartnerTrainingModule
from userprofile.models import Profile
from conf.utils import generate_numeric


class Cooperative(models.Model):
    name = models.CharField(max_length=150, unique=True)
    logo = models.ImageField(upload_to='cooperatives/', null=True, blank=True)
    code = models.CharField(max_length=150, unique=True, null=True, blank=True)
    coop_abbreviation = models.CharField(max_length=150, unique=True, null=True, blank=True)
    district = models.ForeignKey(District, null=True, blank=True, on_delete=models.CASCADE)
    sub_county = models.ForeignKey(SubCounty, null=True, blank=True, on_delete=models.CASCADE)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=12, null=True, blank=True)
    contact_person_name = models.CharField(max_length=150)
    product = models.ManyToManyField(Product, blank=True)
    contribution_total = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    shares = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    is_active = models.BooleanField(default=0)
    send_message = models.BooleanField(default=0,
                                       help_text='If not set, the cooperative member will not receive SMS\'s when sent.')
    date_joined = models.DateField()
    sms_api_url = models.CharField(max_length=255, null=True, blank=True)
    sms_api_token = models.CharField(max_length=255, null=True, blank=True)
    payments_account = models.CharField(max_length=255, null=True, blank=True)
    payments_token = models.CharField(max_length=255, null=True, blank=True)
    payments_authentication = models.CharField(max_length=255, null=True, blank=True)
    system_url = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    get_external_data = models.BooleanField(default=False)
    external_data_url = models.CharField(max_length=255, null=True, blank=True)
    external_data_token = models.CharField(max_length=255, null=True, blank=True)

    mobis_slug = models.CharField(max_length=255, null=True, blank=True)
    mobis_username = models.CharField(max_length=255, null=True, blank=True)
    mobis_password = models.CharField(max_length=255, null=True, blank=True)

    trust_network_id = models.CharField(max_length=255, null=True, blank=True)
    saving_product = models.CharField(max_length=255, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative'
        
    def __unicode__(self):
        return self.name

    def agents_count(self):
        agent = CooperativeAdmin.objects.filter(cooperative=self, user__profile__access_level__name='AGENT')
        return agent.count()

    def member_count(self):
        members = CooperativeMember.objects.filter(cooperative=self)
        return members.count()

    def male_count(self):
        members = CooperativeMember.objects.filter(cooperative=self, gender="Male")
        return members.count()

    def female_count(self):
        members = CooperativeMember.objects.filter(cooperative=self, gender="Female")
        return members.count()

    def refugee_count(self):
        members = CooperativeMember.objects.filter(cooperative=self, is_refugee=True)
        return members.count()

    def handicup_count(self):
        members = CooperativeMember.objects.filter(cooperative=self, is_handicap=True)
        return members.count()

    def youth_count(self):
        low = datetime.today() - relativedelta(years = 15)
        high = datetime.today() - relativedelta(years = 30)
        members = CooperativeMember.objects.filter(cooperative=self, date_of_birth__lte=low, date_of_birth__gte=high)
        # members = CooperativeMember.objects.filter(cooperative=self, date_of_birth__gte=high)
        if self.id == 1:
            return members.count() + 5
        else:
            return members.count() + 6
    

class CooperativeSharePrice(models.Model):
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    current = models.BooleanField(default=0)
    remark = models.CharField(max_length=120)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_share_price'
        unique_together = ['price', 'current']
    
    def __unicode__(self):
        return u'%s' % self.price
    

class AnimalIdentification(models.Model):
    method = models.CharField('Method', max_length=50)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'animal_identification'
        
    def __unicode__(self):
        return self.method
    

class TickControl(models.Model):
    method = models.CharField('Method', max_length=50)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tick_control'
        
    def __unicode__(self):
        return self.method


class CommonDisease(models.Model):
    name = models.CharField(max_length=120, unique=True)
    local = models.CharField('Local Name', max_length=160, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'common_diseases'
    
    def __unicode__(self):
        return u"%s|%s" % (self.name, self.local)


class CooperativeAdmin(models.Model):
    user = models.OneToOneField(User,  blank=True, related_name='cooperative_admin')
    cooperative = models.ForeignKey(Cooperative, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        db_table = 'cooperative_admin'
        
    def __unicode__(self):
        return u'%s' % self.cooperative


class OtherCooperativeAdmin(models.Model):
    user = models.ForeignKey(User, blank=True, related_name='other_cooperative_admin')
    cooperative = models.ForeignKey(Cooperative, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'other_cooperative_admin'

    def __unicode__(self):
        return u'%s' % self.cooperative


class CooperativeContribution(models.Model):
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    new_balance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    indicator = models.CharField(max_length=120)
    attachment = models.FileField(upload_to='cooperatives/files/', null=True, blank=True)
    remark = models.CharField(max_length=120, null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    transaction_date = models.DateTimeField()
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_contribution'
        
    def __unicode__(self):
        return u'%s' % self.amount 
    


class FarmerGroup(models.Model):
    name = models.CharField(max_length=255)
    cooperative = models.ForeignKey(Cooperative, null=True, blank=True, on_delete=models.SET_NULL)
    code = models.CharField(max_length=150, unique=True, null=True, blank=True)
    district = models.ForeignKey(District, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(County, null=True, blank=True, on_delete=models.CASCADE)
    sub_county = models.ForeignKey(SubCounty, null=True, blank=True, on_delete=models.CASCADE)
    parish = models.ForeignKey(Parish, null=True, blank=True, on_delete=models.CASCADE)
    village = models.CharField(max_length=255, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=12, null=True, blank=True)
    contact_person_name = models.CharField(max_length=150)
    contact_person_number = models.CharField(max_length=150)
    product = models.ManyToManyField(Product, blank=True)
    contribution_total = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    shares = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    is_active = models.BooleanField(default=0)
    send_message = models.BooleanField(default=0,
                                       help_text='If not set, the cooperative member will not receive SMS\'s when sent.')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'farmer_group'

    def __unicode__(self):
        return "{} ({})".format(self.name, self.village)

    def __str__(self):
        return self.__unicode__()

    def member_count(self):
        count = CooperativeMember.objects.filter(farmer_group=self).count()
        return count

class CooperativeShareTransaction(models.Model):
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=254, null=True, blank=True)
    share_value = models.DecimalField(max_digits=20, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=20, decimal_places=2)
    shares_bought = models.DecimalField(max_digits=20, decimal_places=2)
    new_shares = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    transaction_date = models.DateTimeField()
    created_by = models.ForeignKey(User,  null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_share_transaction'
        
    def __unicode__(self):
        return u'%s' % self.shares_bought
                              

class CooperativeTrainingModule(models.Model):
    module = models.CharField(max_length=150)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_training_module'
        
    def __unicode__(self):
        return self.module
    
        
class CooperativeMember(models.Model):
    title = (
        ('Mr', 'Mr'),
        ('Miss', 'Miss'),
        ('Mrs', 'Mrs'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
        ('Hon', 'Hon'),
    )
    months_choices = []
    for i in range(1, 13):
        months_choices.append((i, calendar.month_name[i]))


    cooperative = models.ForeignKey(Cooperative, null=True, blank=True, on_delete=models.CASCADE)
    farmer_group = models.ForeignKey(FarmerGroup, null=True, blank=True, on_delete=models.SET_NULL)
    image = models.ImageField(upload_to='member/', null=True, blank=True)
    member_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    title = models.CharField(max_length=25, choices=title, null=True, blank=True)
    surname = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    other_name = models.CharField(max_length=150, null=True, blank=True)
    is_refugee = models.BooleanField(default=False)
    is_handicap = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=(('Male', 'Male'), ('Female', 'Female')), null=True, blank=True)
    maritual_status = models.CharField(max_length=10, null=True, blank=True, choices=(('Single', 'Single'), ('Married', 'Married'),
        ('Widowed', 'Widow'), ('Divorced', 'Divorced')))
    id_number = models.CharField(max_length=150, null=True, blank=True, unique=True)
    id_type = models.CharField(max_length=150, null=True, blank=True, choices=(('nin', 'National ID'), ('dl', 'Drivers Lisence'),
        ('pp', 'PassPort'), ('o', 'Other')))
    phone_number = models.CharField(max_length=12, null=True, blank=True)
    other_phone_number = models.CharField(max_length=12, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    district = models.ForeignKey(District, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(County, null=True, blank=True, on_delete=models.CASCADE)
    sub_county = models.ForeignKey(SubCounty, null=True, blank=True, on_delete=models.CASCADE)
    parish = models.ForeignKey(Parish, null=True, blank=True, on_delete=models.CASCADE)
    village = models.CharField(max_length=150, null=True, blank=True)
    address = models.CharField(max_length=150, null=True, blank=True)
    gps_coodinates = models.CharField(max_length=150, null=True, blank=True)
    coop_role = models.CharField(max_length=150, choices=(('Chairperson', 'Chairperson'), ('Vice', 'Vice'), ('Treasurer', 'Treasurer'),
        ('Secretary', 'Secretary'), ('Committee Member', 'Committee Member'),  ('Member', 'Member')))
    year_joined = models.PositiveIntegerField(null=True, blank=True)
    month_joined = models.PositiveIntegerField(null=True, blank=True, choices=months_choices)
    land_acreage = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    product = models.CharField(max_length=255, null=True, blank=True)
    shares = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    share_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    collection_amount = models.DecimalField(max_digits=32, decimal_places=2, default=0, blank=True)
    collection_quantity = models.DecimalField(max_digits=32, decimal_places=2, default=0, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    account = models.OneToOneField(Account, null=True, blank=True, related_name="member_account")
    borrower_id = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=1)
    has_insurance = models.BooleanField(default=0)
    qrcode = models.ImageField(upload_to='qrcode', blank=True, null=True)
    app_id = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    ensuubuko_id = models.CharField(max_length=255, null=True, blank=True)
    ensuubuko_customer_id = models.CharField(max_length=255, null=True, blank=True)
    ensuubuko_info = models.TextField(null=True, blank=True)
    ensuubuko_savings = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    ensuubuko_savings_id = models.PositiveIntegerField(null=True, blank=True)
    ensuubuko_savings_product = models.PositiveIntegerField(default=1, null=True, blank=True)
    create_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member'

    def __unicode__(self):
        return "{} {} {}".format(self.surname, self.first_name, self.other_name)
    
    def get_name(self):
        return "%s %s %s" % (self.surname, self.first_name, self.other_name if self.other_name else "")

    def get_absolute_url(self):
        return reverse('events.views.details', args=[str(self.id)])

    @property
    def age(self):
        if self.date_of_birth:
            m = date.today() - self.date_of_birth
            return m.days / 365
        return 40

    def generate_qrcode(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=0,
        )
        qr.add_data(self.member_id)
        qr.make(fit=True)

        img = qr.make_image()

        buffer = StringIO.StringIO()
        img.save(buffer)
        filename = '%s-%s_%s.png' % (self.member_id, self.surname, self.first_name)
        filebuffer = InMemoryUploadedFile(
            buffer, None, filename, 'image/png', buffer.len, None)
        self.qrcode.save(filename, filebuffer)
    
    def get_qrcode(self):
        if not self.qrcode:
            self.generate_qrcode()
        return self.qrcode
    
    def get_member_busines(self):
        try:
            return CooperativeMemberBusiness.objects.get(cooperative_member=self)
        except Exception:
            return None
    
    def get_collections(self):
        return Collection.objects.filter(member=self)
    
    def get_member_products(self):
        return CooperativeMemberProductDefinition.objects.filter(cooperative_member=self)
    
    def get_member_herd_male(self):
        return CooperativeMemberHerdMale.objects.filter(cooperative_member=self)
    
    def get_member_herd_female(self):
        return CooperativeMemberHerdFemale.objects.filter(cooperative_member=self)
    
    def get_member_shares(self, ):
        return CooperativeMemberSharesLog.objects.filter(cooperative_member=self)
    
    def get_deworm_schedule(self, ):
        return DewormingSchedule.objects.filter(cooperative_member=self)
    
    def get_member_prev_supply(self):
        try:
            return CooperativeMemberSupply.objects.get(cooperative_member=self)
        except Exception:
            return None
    
    def get_order(self):
        try:
            return MemberOrder.objects.filter(member=self).order_by('-order_date')
        except Exception:
            return None

    def get_insurance(self):
        try:
            return OKOMemberPolicy.objects.filter(cooperative_member=self).order_by('-create_date')
        except Exception:
            return None


    # def get_total_product(self):
    #     q = CooperativeMemberProductQuantity.objects.filter(cooperative_member=self)
    #     tp = q.annotate(total_product=F('adult')+F('heifer')+F('bullock')+F('calves'))
    #     
    #     total = 0
    #     for x in tp:
    #         total = x.total_product
    #     return total


@receiver(post_save, sender=CooperativeMember)
def create_account(sender, instance, created, **kwargs):
    today = datetime.now()
    lrq = Account.objects.all()
    ln_cnt = "%s%s" % (generate_numeric(2), format(lrq.count() + 1, '04'))
    account_number = "MBR/%s/%s" % (today.strftime("%y"), ln_cnt)

    if created:
        acc = Account.objects.create(account_number=account_number, balance=0)
        instance.account=acc
        instance.save()
    else:
        acc = Account.objects.filter(account_number=account_number)
        if acc.count() < 1:
            pass
            # acc = Account.objects.create(account_number=account_number, balance=0)
            # instance.account = acc
            # instance.save()


@receiver(post_save, sender=CooperativeMember)
def save_account(sender, instance, **kwargs):
    today = datetime.now()
    lrq = Account.objects.all()
    ln_cnt = lrq.count() + 1
    account_number = "MBR/%s/%s" % (today.strftime("%y"), format(ln_cnt, '04'))

    if not instance.account:
        acc = Account.objects.create(account_number=account_number, balance=0)
        instance.account = acc
        instance.save()


class OKOMemberPolicy(models.Model):
    cooperative_member = models.OneToOneField(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    policyId = models.CharField('Farm Name', max_length=12, unique=True, null=True, blank=True)
    amount_due = models.DecimalField(max_digits=9, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    claim_status = models.PositiveIntegerField(default=1)
    end_date = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oko_policy'

    def __unicode__(self):
        return self.policyId or u''


class CooperativeMemberBusiness(models.Model):
    cooperative_member = models.OneToOneField(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    business_name = models.CharField('Farm Name', max_length=12, unique=True, null=True, blank=True)
    farm_district = models.ForeignKey(District,  null=True, blank=True, on_delete=models.CASCADE)
    farm_sub_county = models.ForeignKey(SubCounty, null=True, blank=True, on_delete=models.CASCADE)
    gps_coodinates = models.CharField(max_length=150, null=True, blank=True, help_text='Seperate Longinture and Latitude values with a comma(,). Longitude values come first.')
    size = models.DecimalField('Size of Farm', max_digits=10, decimal_places=2)
    size_units = models.CharField(max_length=150, null=True, blank=True, choices=(('acre', 'Acres'), ('ha', 'Hectare'), ('sq_m', 'Square Meters'), ('sq_km', 'Square Kilometers')))
    fenced = models.BooleanField(default=0)
    paddock = models.BooleanField(default=0)
    water_source = models.CharField(max_length=12, null=True, blank=True, choices=(('Dam', 'Dam'), ('Spring', 'Spring'), ('Rain', 'Rain'), ('Swamp', 'Swamp')))
    animal_identification = models.CharField(max_length=12, null=True, blank=True)
    common_diseases = models.ManyToManyField(CommonDisease, blank=True)
    other_animal_diseases = models.TextField('Other Common Disease Specify', null=True, blank=True)
    tick_control = models.CharField(max_length=12, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_business'
        
    def __unicode__(self):
        return self.business_name or u''
    

class DewormingSchedule(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    deworm_date = models.DateField(null=True, blank=True)
    dewormer = models.CharField(max_length=128, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'deworming_schedule'
    
    def __unicode__(self):
        return u'%s' % self.deworm_date or u''
    

class CooperativeMemberProductDefinition(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    product_variation = models.ManyToManyField(ProductVariation, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_product_definition'
    
    def __unicode__(self):
        return 'Beeds' or u''
    
        
class CooperativeMemberProductQuantity(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=(('Male','Male'), ('Female','Female')), null=True, blank=True)
    adult = models.PositiveIntegerField(default=0, blank=True)
    heifer = models.PositiveIntegerField(default=0, blank=True)
    bullock = models.PositiveIntegerField(default=0, blank=True)
    calves = models.PositiveIntegerField(default=0, blank=True)
    total = models.PositiveIntegerField(default=0, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_product_quantity'
        
    def __unicode__(self):
        return self.gender or u''


class CooperativeMemberHerdMale(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    adults = models.PositiveIntegerField(default=0, blank=True)
    bullocks = models.PositiveIntegerField(default=0, blank=True)
    calves = models.PositiveIntegerField(default=0, blank=True)
    total = models.PositiveIntegerField(default=0, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'herd_male'
    
    def __unicode__(self):
        return u'%s' % self.total or u''


class CooperativeMemberHerdFemale(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    f_adults = models.PositiveIntegerField('Adults', default=0, blank=True)
    heifers = models.PositiveIntegerField(default=0, blank=True)
    f_calves = models.PositiveIntegerField('Calves', default=0, blank=True)
    f_total = models.PositiveIntegerField('Total', default=0, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'herd_female'
    
    def __unicode__(self):
        return self.f_total or u''
    
    
# class CooperativeMemberHerd(models.Model):
#     cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True)
#     male_adults = models.PositiveIntegerField(default=0, blank=True)
#     male_bullocks = models.PositiveIntegerField(default=0, blank=True)
#     male_calves = models.PositiveIntegerField(default=0, blank=True)
#     female_adults = models.PositiveIntegerField(default=0, blank=True)
#     female_heifers = models.PositiveIntegerField(default=0, blank=True)
#     female_calves = models.PositiveIntegerField(default=0, blank=True)
#     total = models.PositiveIntegerField(default=0, blank=True)
#     create_date = models.DateTimeField(auto_now_add=True)
#     update_date = models.DateTimeField(auto_now=True)

class CooperativeMemberProduct(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    product_variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)
    gender = models.CharField(max_length=12, choices=(('Male', 'Male'), ('Female', 'Female')))
    animal_type = models.CharField(max_length=12, choices=(('Adult', 'Adults'), ('Bullock', 'Bullocks'), ('Calf', 'Calfs')))
    quantity = models.PositiveIntegerField()
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_product'
        unique_together = ['cooperative_member', 'product_variation', 'gender', 'animal_type']
    
    def __unicode__(self):
        return self.gender or u''
    

class CooperativeMemberSupply(models.Model):
    
    cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    nearest_market = models.CharField(max_length=150, null=True, blank=True)
    product_average_cost = models.DecimalField('Estimate Cost per Animal', max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_kilo = models.DecimalField('Estimate cost Per Kilo', max_digits=10, decimal_places=2, null=True, blank=True)
    probable_sell_month = models.CharField(max_length=250, null=True, blank=True)
    # sell_mode = models.CharField(max_length=150, null=True, blank=True)
    # sell_to_union_partner = models.BooleanField(default=0)
    sell_to_cooperative_society = models.BooleanField(default=0)
    # prefered_payment_method = models.CharField(max_length=150, null=True, blank=True, help_text='How You wish the Society to Pay')
    # weight_measurement_mode = models.CharField(max_length=150, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_supply'
        
    def __unicode__(self):
        return self.nearest_market or u''
        

# class CooperativeMemberTraining(models.Model):
#     cooperative_member = models.ForeignKey(CooperativeMember, null=True, blank=True)
#     attended_partner_training = models.BooleanField(default=0)
#     # partner_training = models.ManyToManyField(PartnerTrainingModule, blank=True)
#     cooperatve_training = models.ManyToManyField(CooperativeTrainingModule, blank=True)
#     create_date = models.DateTimeField(auto_now_add=True)
#     update_date = models.DateTimeField(auto_now=True)
#     
#     class Meta:
#         db_table = 'cooperative_member_training'
#     
#     def __unicode__(self):
#         return self.attended_partner_training or u''
        

class CooperativeMemberSubscriptionLog(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=254, null=True, blank=True)
    year = models.PositiveIntegerField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField()
    received_by = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE, related_name='receiver')
    remark = models.CharField(max_length=160, null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_subscription_log'
        unique_together = ['cooperative_member', 'year']
    
    def __unicode__(self):
        return u'%s' % self.transaction_id or u''


class CooperativeMemberSharesLog(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=254, null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMethod, null=True, blank=True, on_delete=models.CASCADE)
    shares_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    shares = models.DecimalField(max_digits=10, decimal_places=2)
    new_shares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    transaction_date = models.DateTimeField()
    remark = models.CharField(max_length=160, null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_shares_log'
        
    def __unicode__(self):
        return u'%s' % self.transaction_id or u''


class MemberSupplySchedule(models.Model):
    pass

    class Meta:
        db_table = 'cooperative_member_supply_schedule'


class MemberSupplyRequest(models.Model):
    cooperative_member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    transaction_reference = models.CharField(max_length=254, null=True, blank=True)
    supply_date = models.DateField()
    status = models.CharField(max_length=15, choices=(('PENDING', 'PENDING'), ('ACCEPTED', 'ACCEPTED'), ('REJECTED', 'REJECTED')), default='PENDING', blank=True)
    confirmed_by = models.CharField(max_length=120, null=True, blank=True)
    confirmation_logged_by = models.ForeignKey(User, null=True, blank=True, related_name='confirmer', on_delete=models.CASCADE)
    comfirmation_method = models.CharField(max_length=120, null=True, blank=True)
    remark = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cooperative_member_supply_request'
        
    def __unicode__(self):
        return self.transaction_reference or u''
    
    def get_variation(self):
        return MemberSupplyRequestVariation.objects.filter(supply_request=self)
    
    def get_sum_total(self):
        ms =  MemberSupplyRequestVariation.objects.filter(supply_request=self).aggregate(total_amount=Sum('total'))
        return ms['total_amount']
    
    def remaining_days(self):
        d0 = datetime.now().date()
        d1 = self.supply_date
        delta = d1 - d0
        return delta.days    
    

class MemberSupplyRequestVariation(models.Model):
    supply_request = models.ForeignKey(MemberSupplyRequest, blank=True, null=True, on_delete=models.CASCADE)
    breed = models.ForeignKey(ProductVariation, null=True, blank=True, on_delete=models.CASCADE)
    total = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)                            
    
    class Meta:
        db_table = 'member_supply_request_variation'
        
    def __unicode__(self):
        return "%s" % self.supply_request or u''


class Collection(models.Model):
    collection_date = models.DateTimeField()
    is_member = models.BooleanField(default=1)
    cooperative = models.ForeignKey(Cooperative, null=True, blank=True, on_delete=models.CASCADE)
    member = models.ForeignKey(CooperativeMember, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=30, null=True, blank=True)
    collection_reference = models.CharField(max_length=255, blank=True)
    product = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=20, decimal_places=2)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    total_price = models.DecimalField(max_digits=20, decimal_places=2)
    created_by = models.ForeignKey(User, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now = True)
    
    class Meta:
        db_table = 'collection'
        


class MemberTransaction(models.Model):
    member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=16)
    transaction_reference = models.CharField(max_length=120)
    entry_type = models.CharField(max_length=120)
    balance_before = models.DecimalField(max_digits=32, decimal_places=2)
    amount = models.DecimalField(max_digits=32, decimal_places=2)
    balance_after = models.DecimalField(max_digits=32, decimal_places=2)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'member_transaction'
        
    def __unicode__(self):
        return "%s" % self.transaction_type or u''
    

class MemberOrder(models.Model):
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE)
    member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    order_reference = models.CharField(max_length=255, blank=True)
    order_price = models.DecimalField(max_digits=20, decimal_places=2, default=0, blank=True)
    request_type = models.CharField(max_length=120, choices=[['LOAN', 'LOAN'], ['CASH', 'CASH'], ['MOBILE_MONEY', 'MOBILE_MONEY']], default="LOAN")
    status = models.CharField(max_length=255, default='PENDING')
    order_date = models.DateTimeField()

    confirmed_by = models.ForeignKey(User, related_name="user_confirm", null=True, blank=True)
    accept_date = models.DateTimeField(null=True, blank=True)
    reject_date = models.DateTimeField(null=True, blank=True)
    reject_reason = models.CharField(max_length=120, null=True, blank=True)

    approve_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, related_name="approver", null=True, blank=True)
    approval_reject_reason = models.CharField(max_length=120, null=True, blank=True)

    accept_processing_by = models.ForeignKey(User, related_name="processor", null=True, blank=True)
    processing_start_date = models.DateTimeField(null=True, blank=True)
    processing_reject_reason = models.CharField(max_length=120, null=True, blank=True)

    ship_date = models.DateTimeField(null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    delivery_accept_date = models.DateTimeField(null=True, blank=True)
    delivery_reject_date = models.DateTimeField(null=True, blank=True)
    delivery_reject_reason = models.CharField(max_length=120, null=True, blank=True)
    collect_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'member_order'
        
    def __unicode__(self):
        return "%s" % self.order_reference or u''
    
    def get_orders(self):
        return OrderItem.objects.filter(order=self)

    @property
    def get_supplier_orders(self, supplier):
        order = OrderItem.objects.filter(item__supplier=supplier)
        if order.exits():
            return order.count()
        return 0

    
class OrderItem(models.Model):
    order = models.ForeignKey(MemberOrder, blank=True, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=20, decimal_places=2)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True)
    price = models.DecimalField(max_digits=20, decimal_places=2, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True, default='PENDING')
    confirmed_by = models.ForeignKey(User, related_name="item_user_confirm", null=True, blank=True)
    confirm_date = models.DateTimeField(null=True, blank=True)
    reject_date = models.DateTimeField(null=True, blank=True)
    reject_reason = models.CharField(max_length=120, null=True, blank=True)

    approve_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, related_name="item_approver", null=True, blank=True)
    approval_reject_reason = models.CharField(max_length=120, null=True, blank=True)

    accept_processing_by = models.ForeignKey(User, related_name="item_processor", null=True, blank=True)
    processing_start_date = models.DateTimeField(null=True, blank=True)
    processing_reject_reason = models.CharField(max_length=120, null=True, blank=True)

    ship_date = models.DateTimeField(null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    delivery_accept_date = models.DateTimeField(null=True, blank=True)
    delivery_reject_date = models.DateTimeField(null=True, blank=True)
    delivery_reject_reason = models.CharField(max_length=120, null=True, blank=True)
    collect_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order_item'
        
    def __unicode__(self):
        return "%s" % self.item or u''


# class Transaction(models.Model):
#     transaction_reference = models.CharField(max_length=160)
#     transaction_category = models.CharField(max_length=120)
#     amount = models.DecimalField(max_digits=12, decimal_places=2)
#     entry_type = models.CharField(max_length=64, null=True, blank=True)
#     members = models.ForeignKey(CooperativeMember, null=True, blank=True)
#     user = models.ForeignKey(User, null=True, blank=True)
#     description = models.CharField(max_length=255, null=True, blank=True)
#     created_by = models.ForeignKey(User, null=True, blank=True, related_name="transaction_user")
#     created_by_name = models.CharField(max_length=160, null=True, blank=True)
#     create_date = models.DateTimeField(auto_now_add=True)
#     update_date = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         db_table = 'transaction'
#
#     def __unicode__(self):
#         return "%s" % self.transaction_reference
#
#
# class Account(models.Model):
#     account_number = models.CharField(max_length=255, unique=True)
#     balance = models.DecimalField(max_digits=12, decimal_places=2)
#

class ProfileManager(models.Manager):
    def get_queryset(self):
        return super(ProfileManager, self).get_queryset().filter(Q(access_level__name ='COOPERATIVE')|Q(access_level__name ='AGENT')|Q(access_level__name ='UNION'))


class Agent(Profile):
    objects = ProfileManager()

    class Meta:
        proxy = True

    def members(self):
        members = CooperativeMember.objects.filter(create_by=self.user)
        return members.count()