import json
import requests
from conf.utils import log_debug, log_error


class FamuneraAPI:

    token = None
    url = None

    def __init__(self, params):
        self.token = params.get('token')
        self.url = "https://api.famunera.com/partner/v1"

    def create_token(self, credentials):
        clientId = credentials.get('clientId')
        clientSecret = credentials.get('clientSecret')
        self.url = self.url + "/auth/token"
        header = {
            'clientId': clientId,
            'clientSecret': clientSecret
        }
        print(header)
        response = self.get_request(header)
        print(response)
        if response.get('status') == 200:
            return response
        return ""

    def get_items(self, category):
        self.url = self.url + "/items/?category=%s/" % category
        header = {
            'Authorization': "Bearer %s" % self.token
        }
        print(self.url)
        response = self.get_request(header)
        print(response)
        if response.get('status') == 200:
            return response
        return ""

    def get_categories(self):
        self.url = self.url + "/categories"
        header = {
            'Authorization': "Bearer %s" % self.token
        }
        response = self.get_request(header)
        if response.get('status') == 200:
            return response
        return ""

    def get_regions(self):
        pass

    def create_order(self):
        pass

    def check_order(self):
        pass

    def get_request(self, header):
        try:
            response = requests.get(self.url, headers=header, verify=False)
            log_debug(response.content)
            return json.loads(response.content)
        except Exception as e:
            log_error()
            return {"status": 404, "message": e}

