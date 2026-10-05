from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce


class Category(models.Model):
	INCOME = 'income'
	EXPENSE = 'expense'
	BOTH = 'both'
	KIND_CHOICES = [
		(INCOME, 'Entrada'),
		(EXPENSE, 'Saída'),
		(BOTH, 'Ambos'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='finance_categories')
	name = models.CharField(max_length=40)
	kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=EXPENSE)
	color = models.CharField(
		max_length=7,
		default='#64748b',
		validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Use uma cor hexadecimal, como #64748b.')],
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']
		constraints = [models.UniqueConstraint(fields=['user', 'name', 'kind'], name='unique_category_name_per_user_kind')]

	def __str__(self):
		return self.name


class Account(models.Model):
	CHECKING = 'checking'
	SAVINGS = 'savings'
	CASH = 'cash'
	INVESTMENT = 'investment'
	ACCOUNT_TYPES = [
		(CHECKING, 'Conta corrente'),
		(SAVINGS, 'Poupança'),
		(CASH, 'Dinheiro'),
		(INVESTMENT, 'Investimento'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='finance_accounts')
	name = models.CharField(max_length=80)
	account_type = models.CharField(max_length=12, choices=ACCOUNT_TYPES, default=CHECKING)
	opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	allow_overdraft = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']
		constraints = [models.UniqueConstraint(fields=['user', 'name'], name='unique_account_name_per_user')]

	@property
	def balance(self):
		transactions = self.transactions.aggregate(
			income=Coalesce(Sum('amount', filter=models.Q(kind=Transaction.INCOME)), Decimal('0.00')),
			expenses=Coalesce(Sum('amount', filter=models.Q(kind=Transaction.EXPENSE)), Decimal('0.00')),
		)
		return self.opening_balance + transactions['income'] - transactions['expenses']

	def clean(self):
		if self.pk and not self.allow_overdraft and self.balance < 0:
			raise ValidationError({'opening_balance': 'O saldo inicial não pode deixar a conta com saldo negativo.'})

	def __str__(self):
		return self.name


class CreditCard(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_cards')
	name = models.CharField(max_length=80)
	credit_limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
	billing_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(28)])
	due_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(28)])
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']
		constraints = [models.UniqueConstraint(fields=['user', 'name'], name='unique_credit_card_name_per_user')]

	@property
	def used_limit(self):
		return self.transactions.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']

	@property
	def available_limit(self):
		return self.credit_limit - self.used_limit

	def clean(self):
		if self.pk and self.used_limit > self.credit_limit:
			raise ValidationError({'credit_limit': 'O limite não pode ficar abaixo do valor já utilizado.'})

	def __str__(self):
		return self.name


class Budget(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
	category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='budgets')
	amount_limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
	start_date = models.DateField()
	end_date = models.DateField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-start_date', 'category__name']
		constraints = [models.UniqueConstraint(fields=['user', 'category', 'start_date', 'end_date'], name='unique_budget_period_per_category')]

	def clean(self):
		errors = {}
		if self.category_id and self.user_id:
			if self.category.user_id != self.user_id:
				errors['category'] = 'A categoria deve pertencer ao usuário atual.'
			elif self.category.kind not in (Category.EXPENSE, Category.BOTH):
				errors['category'] = 'Orçamentos só podem usar categorias de saída.'
		if self.start_date and self.end_date and self.end_date < self.start_date:
			errors['end_date'] = 'A data final deve ser igual ou posterior à data inicial.'
		if errors:
			raise ValidationError(errors)

	def __str__(self):
		return f'{self.category}: {self.amount_limit}'


class Transaction(models.Model):
	INCOME = 'income'
	EXPENSE = 'expense'
	KIND_CHOICES = [
		(INCOME, 'Entrada'),
		(EXPENSE, 'Saída'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
	description = models.CharField(max_length=120)
	amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
	kind = models.CharField(max_length=10, choices=KIND_CHOICES)
	category = models.CharField(max_length=40, default='Geral')
	category_item = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
	account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
	credit_card = models.ForeignKey(CreditCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
	occurred_at = models.DateField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-occurred_at', '-created_at']
		indexes = [models.Index(fields=['user', 'occurred_at']), models.Index(fields=['user', 'kind'])]

	def clean(self):
		errors = {}
		if self.category_item_id and self.user_id:
			if self.category_item.user_id != self.user_id:
				errors['category_item'] = 'A categoria deve pertencer ao usuário atual.'
			elif self.category_item.kind not in (self.kind, Category.BOTH):
				errors['category_item'] = 'A categoria não corresponde ao tipo da movimentação.'
		if self.account_id and self.account.user_id != self.user_id:
			errors['account'] = 'A conta deve pertencer ao usuário atual.'
		if self.credit_card_id:
			if self.credit_card.user_id != self.user_id:
				errors['credit_card'] = 'O cartão deve pertencer ao usuário atual.'
			elif self.kind != self.EXPENSE:
				errors['credit_card'] = 'Cartões só podem ser usados em saídas.'
		if self.account_id and self.credit_card_id:
			errors['credit_card'] = 'Escolha uma conta ou um cartão, não ambos.'

		if self.account_id and not self.account.allow_overdraft and self.kind == self.EXPENSE and self.amount:
			other_transactions = self.account.transactions.exclude(pk=self.pk).aggregate(
				income=Coalesce(Sum('amount', filter=models.Q(kind=self.INCOME)), Decimal('0.00')),
				expenses=Coalesce(Sum('amount', filter=models.Q(kind=self.EXPENSE)), Decimal('0.00')),
			)
			available = self.account.opening_balance + other_transactions['income'] - other_transactions['expenses']
			if self.amount > available:
				errors['amount'] = 'A saída excede o saldo disponível na conta.'

		if self.credit_card_id and self.kind == self.EXPENSE and self.amount:
			used = self.credit_card.transactions.exclude(pk=self.pk).aggregate(
				total=Coalesce(Sum('amount'), Decimal('0.00')),
			)['total']
			if self.amount > self.credit_card.credit_limit - used:
				errors['amount'] = 'A compra excede o limite disponível no cartão.'
		if errors:
			raise ValidationError(errors)

	def __str__(self):
		return f'{self.description} - {self.amount}'
"""Custom user-related models can be defined here when needed."""