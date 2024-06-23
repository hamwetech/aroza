import json
import requests
from api.models import MobisApiRequest
from conf.utils import log_debug, log_error

class Mobis:
    sacco_slug = None
    username = None
    password = None
    url = "https://mobis.stg.ensibuukotech.com/api/v1"
    token = None

    def __init__(self, slug, username, password):
        self.sacco_slug = slug
        self.username = username
        self.password = password
        self.authenticate()

    def authenticate(self):

        self.url ="%s/user/login" % self.url

        pay_load = {
            "sacco_slug": self.sacco_slug,
            "username": self.username,
            "password": self.password
        }

        result = self.make_request(pay_load)
        if not "errors" in result:
            self.token = result.get('api_token')

    def create_individual(self, params):
        self.url = "%s/customers/individuals" % self.url
        if not self.token:
            return {"error": True, "message": "Token not created"}
        try:
            payload = {
                "branch_id": params.get('branch_id'),
                "title": "",
                "first_name": params.get('first_name'),
                "middle_name": params.get('other_name'),
                "last_name": params.get('surname'),
                "dob": params.get('date_of_birth'),
                "gender": params.get('gender'),
                "phone_number": params.get('phone_number'),
                "mobile_money_num": params.get('mobile_money_num'),
                "city": params.get('district'),
                "district": params.get('district'),
                "country": params.get('country'),
                "kin_full_name": params.get('kin_full_name'),
                "kin_phone_number": params.get('phone_number'),
                "registration_date": params.get('registration_date'),
                "legacy_member_num": params.get('member_id'),
                "is_subscribed_sms": "0"
            }
            result = self.make_request(payload)

            if result.get('status-code')==201:
                result.update({"error": False})
            else:
                result.update({"error": True})
            return result
        except Exception as e:
            log_error()
            return {"error": True, "message": "Contact admin. Error: %s" % e}

    def create_savings_account(self, params):
        self.url = "%s/customers/individuals/%s/savings-account" %  (self.url, params.get('customer_id'))
        if not self.token:
            return {"error": True, "message": "Token not created"}
        try:
            payload = {
                "account_name": params.get('account_name'),
                "branch_id": params.get('branch_id'),
                # "customer_id": params.get('customer_id'),
                "opened_at": params.get('opened_at'),
                "opening_balance": params.get('opening_balance'),
                "savings_product_id": params.get('savings_product_id') #Add this to the system setup
            }
            result = self.make_request(payload)

            if result.get('status-code')==201:
                result.update({"error": False})
            else:
                result.update({"error": True})
            return result
        except Exception as e:
            log_error()
            return {"error": True, "message": "Contact admin. Error: %s" % e}

    def credit_savings_account(self, params):
        self.url = "%s/v1/savings-accounts/%s/deposits" % (self.url, params.get('savings_id'))
        if not self.token:
            return {"error": True, "message": "Token not created"}
        try:
            payload = {
                "amount": params.get('amount'),
                "receipt_number": params.get('receipt_number'),
                "transaction_date": params.get('transaction_date'),
                "transaction_fee": params.get('transaction_fee'),
                "transaction_method": params.get('transaction_method')
            }
            result = self.make_request(payload)

            # if result.get('status-code')==201:
            #     result.update({"error": False})
            # else:
            #     result.update({"error": True})
            return result
        except Exception as e:
            log_error()
            return {"error": True, "message": "Contact admin. Error: %s" % e}

    def make_request(self, payload):
        reference_code = None
        try:
            status = "SUCCESSFUL"
            message = None
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            if self.token:
                headers.update({"Authorization": "Bearer %s" % self.token})
            pl = json.dumps(payload)
            log_debug(pl)
            log_debug(headers)
            db_rq = MobisApiRequest.objects.create(
                request=pl
            )
            r = requests.post(self.url, data=pl, headers=headers)
            db_rq.response = r.text
            db_rq.save()

            print(r.request.url)
            print(r.request.body)
            print(r.request.headers)
            log_debug("Response: %s" % r.text)


            res = r.json()

            result = res  # {"error": error, "status": status, "message": message, "reference_code": reference_code}
            print(result)
            return result
        except Exception as e:
            result = {"error": True, "status": "INDETERMINATE", "message": "System Error during MM %s Request." % e,
                      "reference_code": None, "error": True}
            log_debug(e)
            return result