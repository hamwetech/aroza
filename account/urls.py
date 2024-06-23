from django.conf.urls import url

from account.views import *

urlpatterns = [
      url(r'transaction/list/$', TransactionListview.as_view(), name="transaction_list"),
      url(r'transaction/savings/create/$', SavingsCreditCreateForm.as_view(), name="savings_create")
]