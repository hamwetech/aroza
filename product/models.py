# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User


class Product(models.Model):
    name = models.CharField(max_length=25, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product'
    
    def product_variation(self):
        return ProductVariation.objects.filter(product=self)

    def __unicode__(self):
        return self.name
    

class ProductUnit(models.Model):
    name = models.CharField(max_length=25, unique=True)
    code = models.CharField(max_length=3, unique=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_units'
        verbose_name = 'Product Unit'
        verbose_name_plural = 'Product Units'
        
    
    def __unicode__(self):
        return self.name
    

class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=25)
    unit = models.ForeignKey(ProductUnit, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variation'
        verbose_name = 'Product'
        verbose_name_plural = 'Product'
        unique_together = ['product', 'name']
           
    def __unicode__(self):
        return self.name
    

class ProductVariationPrice(models.Model):
    product = models.ForeignKey(ProductVariation, related_name='variation_price', on_delete=models.CASCADE)
    unit = models.ForeignKey(ProductUnit, null=True, blank=True, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variation_price'
        verbose_name = 'Product Price'
        verbose_name_plural = 'Product Prices'
        unique_together = ['product', 'unit']
        
    def __unicode__(self):
        return "%s" % self.product


class ProductVariationPriceLog(models.Model):
    product = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)
    unit = models.ForeignKey(ProductUnit, null=True, blank=True, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variation_price_log'
        verbose_name = 'Product Price'
        verbose_name_plural = 'Product Prices'
        
    def __unicode__(self):
        return "%s" % self.product


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    email = models.CharField(max_length=32, null=True, blank=True)
    contact_person = models.CharField(max_length=32, null=True, blank=True)
    contact_person_phone_number = models.CharField(max_length=32, null=True, blank=True)
    logo = models.ImageField(upload_to='supplier/logo/', null=True, blank=True)
    api_url = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    token = models.TextField(blank=True, null=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'supplier'
        
    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class SupplierAdmin(models.Model):
    user = models.OneToOneField(User,  blank=True, related_name='supplier_admin')
    supplier = models.ForeignKey(Supplier, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s" % self.user.get_full_name()


class ItemCategory(models.Model):
    parent = models.ForeignKey('self', null=True, blank=True)
    category_name = models.CharField(max_length=255)
    category_code = models.CharField(max_length=120, null=True, blank=True, unique=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item_category"

    def __unicode__(self):
        return self.category_name


class Item(models.Model):
    name = models.CharField(max_length=255)
    supplier_item_id = models.CharField(unique=True, max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(ItemCategory, null=True)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.CASCADE)
    allow_loan_request = models.BooleanField(default=False)
    supplier_price = models.DecimalField(max_digits=20, decimal_places=2)
    price = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=u"Retail Price")
    created_by = models.ForeignKey(User, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'item'

    def __unicode__(self):
        return self.name


class ItemAdditionalCharges(models.Model):
    name = models.CharField(max_length=160)
    charge_type = models.CharField(max_length=36, choices=(('CHARGE', 'CHARGE'), ('DISCOUNT', 'DISCOUNT')))
    value = models.DecimalField(max_digits=12, decimal_places=2)
    value_type = models.CharField(max_length=36, choices=(('AMOUNT', 'AMOUNT'), ('PERCENTAGE', 'PERCENTAGE')))
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'item_addition_charges'

    def __unicode__(self):
        return "{} {}".format(self.value, self.value_type)

    
# @receiver(post_save, sender=ProductVariationPrice)
# def create_price_log(sender, instance, created, **kwargs):
#     if created:
#         ProductVariationPriceLog.objects.create(variation=instance)


class SalesCommission(models.Model):
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.CASCADE)
    category = models.CharField(max_length=64, choices=(('AGENT', 'AGENT'), ('COOPERATIVE', 'COOPERATIVE')))
    commission_value = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=64, choices=(('PERCENT', 'PERCENT'), ('AMOUNT', 'AMOUNT')))
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sale_commission'
        unique_together = ['supplier', 'category']

    def __unicode__(self):
        return self.commission_value


@receiver(post_save, sender=ProductVariationPrice)
def save_price_log(sender, instance, **kwargs):
    ProductVariationPriceLog.objects.create(product=instance.product,
                                            price=instance.price,
                                            unit=instance.unit,
                                            created_by=instance.created_by) 
