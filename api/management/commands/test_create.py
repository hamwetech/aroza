import datetime
from django.core.management.base import BaseCommand, CommandError
from conf.utils import get_consontant_upper
from coop.models import Cooperative
from api.Mobis import Mobis


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        params = {
            "branch_id": 1,
            "title": "",
            "first_name": "Moses",
            "surname": "TEst user",
            "other_name": None,
            "date_of_birth": "2000-03-04",
            "gender": "Male",
            "phone_number": "0752444902",
            "mobile_money_num": None,
            "parish": "Kanjokya",
            "district": "Kampala",
            "country": "Uganda",
            "kin_full_name": "Moses Theegiptian",
            "kin_phone_number": "0752444933",
            "registration_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "member_id": "MEMD001",
            "is_subscribed_sms": "0"
        }

        mobis = Mobis()
        mobis.create_individual(params)