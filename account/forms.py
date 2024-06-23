from django import forms
from coop.models import CooperativeMember
from conf.utils import bootstrapify, internationalize_number, PHONE_REGEX


class SavingsCreditForm(forms.Form):
    cooperative_member = forms.ChoiceField(widget=forms.Select())
    amount = forms.IntegerField()
    transaction_method = forms.ChoiceField(widget=forms.Select())
    phone_number = forms.CharField(max_length=32, required=False)

    def __init__(self, *args, **kwargs):
        super(SavingsCreditForm, self).__init__(*args, **kwargs)
        choices = [['','------------']]
        choices.extend([[c.id, c.get_name()] for c in CooperativeMember.objects.filter(ensuubuko_savings_id__isnull=False)])
        self.fields['cooperative_member'].choices = choices
        self.fields['transaction_method'].choices = [['','-------------------'], ['CASH', 'CASH'], ['MM', 'MOBILE MONEY']]


bootstrapify(SavingsCreditForm)