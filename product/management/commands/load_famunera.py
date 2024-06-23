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
                self.get_categories(supplier.token)

        except Exception as e:
            log_error()

    def get_categories(self, token):
        fapi = FamuneraAPI({"token": token})
        response = fapi.get_categories()
        arr = []
        try:
            with transaction.atomic():
                for res in response.get("data").get('categories'):
                    arr.append({"parent": None, "ID": res.get("ID"), "name": res.get("name")})
                    self.create_category({"parent": None, "ID": res.get("ID"), "name": res.get("name")})
                    if res.get("sub_categories"):
                        for sub1 in res.get("sub_categories"):
                            arr.append({"parent": res.get("ID"), "ID": sub1.get("ID"), "name": sub1.get("name")})
                            self.create_category({"parent": res.get("ID"), "ID": sub1.get("ID"), "name": sub1.get("name")})
                            if sub1.get("sub_categories"):
                                for sub2 in sub1.get("sub_categories"):
                                    arr.append({"parent": sub1.get("ID"), "ID": sub2.get("ID"), "name": sub2.get("name")})
                                    self.create_category(
                                        {"parent": sub1.get("ID"), "ID": sub2.get("ID"), "name": sub2.get("name")})
                                    if sub2.get("sub_categories"):
                                        for sub3 in sub2.get("sub_categories"):
                                            arr.append({"parent": sub2.get("ID"), "ID": sub3.get("ID"), "name": sub3.get("name")})
                                            self.create_category(
                                                {"parent": sub2.get("ID"), "ID": sub3.get("ID"), "name": sub3.get("name")})
        except Exception as e:
            print("Error %s" % e)

    def create_category(self, params):
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
