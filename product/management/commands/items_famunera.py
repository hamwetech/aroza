from django.core.management.base import BaseCommand, CommandError
from conf.utils import get_consontant_upper, log_debug, log_error
from product.models import Supplier, ItemCategory, Item
from django.db import transaction
from product.api.fanumera import FamuneraAPI


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        try:
            supplier = Supplier.objects.get(name="FAMUNERA")
            if supplier:
                self.get_items(supplier.token)

        except Exception as e:
            log_error()

    def get_items(self, token):

        supplier = Supplier.objects.get(name="FAMUNERA")
        categories = ItemCategory.objects.all()

        for category in categories:
            fapi = FamuneraAPI({"token": token})
            ctx = ItemCategory.objects.filter(parent=category)
            # if not ctx.exists():
            response = fapi.get_items("%s" % category.category_code)
            print("%s ===" % response)
            print("LEN %s === %s" % (len(response), category.category_code))
            try:
                with transaction.atomic():
                    if len(response) > 0:
                        if len(response.get('data').get('items')) > 0:
                            for item in response.get('data').get('items'):
                                description = item.get('description')
                                local_price = item.get('local_price')
                                product_name = item.get('product_name')
                                featured_image = item.get('featured_image')
                                supplier_item_id = item.get('ID')
                                print("Saving item id:%s name:%s" % (supplier_item_id, product_name))
                                qr = Item.objects.filter(supplier_item_id=supplier_item_id)
                                if qr.exists():
                                    qr = qr[0]
                                    qr.description = description
                                    qr.supplier_price = local_price
                                    qr.price = local_price
                                    qr.name = product_name
                                    qr.category = category
                                    qr.save()
                                else:
                                    Item.objects.create(
                                        name = product_name,
                                        supplier_item_id=supplier_item_id,
                                        description=description,
                                        category=category,
                                        supplier=supplier,
                                        supplier_price=local_price,
                                        price=local_price,
                                    )

            except Exception as e:
                print("Error %s -- %s" % (category, e))

    def create_item(self, params):
        print("Data %s" % params)
        parent_id = params.get('parent')
        name = params.get('name')
        id = params.get('ID')
        parent = None

        if parent_id:
            parent = ItemCategory.objects.filter(category_code=parent_id)
            if parent.count() > 0:
                parent = parent[0]

        item = ItemCategory.objects.filter(category_code=id)
        if item.exists():
            print("Parent update %s" % parent)
            item.update(category_code=id, category_name=name)
            if parent:
                item.update(parent=parent)
        else:
            it = ItemCategory.objects.create(category_code=id, category_name=name)
            if parent:
                print("Parent %s" % parent)
                it.parent=parent
                it.save()



    def dict_generator(self, indict, pre=None):
        pre = pre[:] if pre else []
        if isinstance(indict, dict):
            for key, value in indict.items():
                if isinstance(value, dict):
                    for d in dict_generator(value, pre + [key]):
                        yield d
                elif isinstance(value, list) or isinstance(value, tuple):
                    for v in value:
                        for d in dict_generator(v, pre + [key]):
                            yield d
                else:
                    yield pre + [key, value]
        else:
            yield pre + [indict]

    def func1(self, data, parent=None):
        for value in data:
            print(str(value.get("ID"))+" --- "+value.get("name")+"----"+str(value.get('sub_categories'))+">>>>>\r\n")
            # if isinstance(value, list):
            #     if len(value) == 1:
            #         print(str(key) + '->' + str(value)+">>>>>\r\n")
            #         # print("++++++++++++++++++++++++++++++++++\r\n")
            if isinstance(value.get('sub_categories'), dict):
                print("===================== Dict \r\r")
                self.func1(value.get('sub_categories'))
            elif isinstance(value.get('sub_categories'), list):
                print(value.get('name')+"===================== List \r\r")
                for val in value.get('sub_categories'):
                    if isinstance(val.get('sub_categories'), str):
                        pass
                    elif isinstance(val.get('sub_categories'), list):
                        print(val.get('name')+" ===================== List 2"+ str(val.get('sub_categories')) +"\r\r")
                        if val.get('sub_categories'):
                            print("===================== Dict 2\r\r")
                            self.func1(val.get('sub_categories'))
                    else:
                        if val.get('sub_categories'):
                            self.func1(val.get('sub_categories'))

    def func1__D(self, data, parent=None):
        for value in data:
            print(str(value.get('sub_categories'))+">>>>>\r\n")
            # if isinstance(value, list):
            #     if len(value) == 1:
            #         print(str(key) + '->' + str(value)+">>>>>\r\n")
            #         # print("++++++++++++++++++++++++++++++++++\r\n")
            if isinstance(value, dict):
                self.func1(value)
            elif isinstance(value, list):
                for val in value:
                    if isinstance(val, str):
                        pass
                    elif isinstance(val, list):
                        pass
                    else:
                        self.func1(val)
