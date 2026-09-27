from django.conf import settings
from django.db import models


class Transaction(models.Model):
	INCOME = 'income'
	EXPENSE = 'expense'
	KIND_CHOICES = [
		(INCOME, 'Entrada'),
		(EXPENSE, 'Saída'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
	description = models.CharField(max_length=120)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	kind = models.CharField(max_length=10, choices=KIND_CHOICES)
	category = models.CharField(max_length=40, default='Geral')
	occurred_at = models.DateField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-occurred_at', '-created_at']

	def __str__(self):
		return f'{self.description} - {self.amount}'
"""Custom user-related models can be defined here when needed."""