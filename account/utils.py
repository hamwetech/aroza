from django.shortcuts import render
from conf.utils import generate_numeric
from account.models import Account, Transaction


def create_transaction(params):
    transaction_reference = generate_numeric(10, "")
    transaction_category = params.get('transaction_category')
    member = params.get('member')
    amount = params.get('amount')
    entry_type = params.get('entry_type')
    description = params.get('description')
    created_by = params.get('created_by')
    created_by_name = params.get('created_by_name')
    new_balance = params.get('new_balance')

    account = member.account

    Transaction.objects.create(
        transaction_reference = transaction_reference,
        transaction_category = transaction_category,
        amount = amount,
        balance_after = new_balance,
        entry_type = entry_type,
        account = account,
        description = description,
        created_by = created_by,
        created_by_name = created_by_name,
    )