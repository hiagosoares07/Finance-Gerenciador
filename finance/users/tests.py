from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import Transaction


class AuthenticationAndDashboardTests(TestCase):
    def test_register_logs_user_in_and_opens_dashboard(self):
        response = self.client.post(
            reverse('users:register'),
            {
                'full_name': 'Ana Souza',
                'email': 'ana@example.com',
                'password': 'S0mething-unique!84',
            },
        )

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        dashboard = self.client.get(reverse('home'))
        self.assertContains(dashboard, 'Olá, Ana.')
        self.assertEqual(dashboard.context['balance'], Decimal('0.00'))

    def test_login_and_logout(self):
        user = get_user_model().objects.create_user(
            username='beto@example.com',
            email='beto@example.com',
            password='S0mething-unique!84',
        )

        response = self.client.post(
            reverse('users:login'),
            {'email': user.email, 'password': 'S0mething-unique!84'},
        )
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('users:login'))

    def test_transactions_change_totals_and_are_private(self):
        owner = get_user_model().objects.create_user(username='owner', password='password')
        other_user = get_user_model().objects.create_user(username='other', password='password')
        self.client.force_login(owner)

        self.client.post(
            reverse('add_transaction'),
            {
                'description': 'Salário',
                'amount': '2500.00',
                'kind': Transaction.INCOME,
                'category': 'Trabalho',
                'occurred_at': '2026-09-10',
            },
        )
        self.client.post(
            reverse('add_transaction'),
            {
                'description': 'Mercado',
                'amount': '300.00',
                'kind': Transaction.EXPENSE,
                'category': 'Casa',
                'occurred_at': '2026-09-11',
            },
        )

        dashboard = self.client.get(reverse('home'))
        self.assertEqual(dashboard.context['balance'], Decimal('2200.00'))
        self.assertEqual(dashboard.context['income_total'], Decimal('2500.00'))
        self.assertEqual(dashboard.context['expense_total'], Decimal('300.00'))

        other_transaction = Transaction.objects.create(
            user=other_user,
            description='Privado',
            amount=Decimal('12.00'),
            kind=Transaction.EXPENSE,
            occurred_at='2026-09-12',
        )
        self.assertEqual(
            self.client.post(reverse('delete_transaction', args=[other_transaction.id])).status_code,
            404,
        )
        self.assertTrue(Transaction.objects.filter(pk=other_transaction.pk).exists())