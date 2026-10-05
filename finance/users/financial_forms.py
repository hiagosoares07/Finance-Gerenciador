from django import forms

from users.models import Account, Budget, Category, CreditCard, Transaction


class OwnerModelForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user or getattr(self.instance, 'user', None)
        if self.user and not self.instance.pk:
            self.instance.user = self.user

        if self.user:
            for field_name in ('category', 'category_item', 'account', 'credit_card'):
                field = self.fields.get(field_name)
                if field is not None and hasattr(field, 'queryset'):
                    field.queryset = field.queryset.filter(user=self.user)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class CategoryForm(OwnerModelForm):
    class Meta:
        model = Category
        fields = ('name', 'kind', 'color')


class AccountForm(OwnerModelForm):
    class Meta:
        model = Account
        fields = ('name', 'account_type', 'opening_balance', 'allow_overdraft')


class CreditCardForm(OwnerModelForm):
    class Meta:
        model = CreditCard
        fields = ('name', 'credit_limit', 'billing_day', 'due_day')


class BudgetForm(OwnerModelForm):
    class Meta:
        model = Budget
        fields = ('category', 'amount_limit', 'start_date', 'end_date')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class TransactionForm(OwnerModelForm):
    class Meta:
        model = Transaction
        fields = ('description', 'amount', 'kind', 'category', 'category_item', 'account', 'credit_card', 'occurred_at')
        widgets = {'occurred_at': forms.DateInput(attrs={'type': 'date'})}

    def clean(self):
        cleaned_data = super().clean()
        category_item = cleaned_data.get('category_item')
        if category_item:
            cleaned_data['category'] = category_item.name
            self.instance.category = category_item.name
        return cleaned_data
