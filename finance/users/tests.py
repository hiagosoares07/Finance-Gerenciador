from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from users.models import Account, Budget, Category, CreditCard, Transaction


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
        today = localdate().isoformat()
        self.client.force_login(owner)

        self.client.post(
            reverse('add_transaction'),
            {
                'description': 'Salário',
                'amount': '2500.00',
                'kind': Transaction.INCOME,
                'category': 'Trabalho',
                'occurred_at': today,
            },
        )
        self.client.post(
            reverse('add_transaction'),
            {
                'description': 'Mercado',
                'amount': '300.00',
                'kind': Transaction.EXPENSE,
                'category': 'Casa',
                'occurred_at': today,
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
            occurred_at=localdate(),
        )
        self.assertEqual(
            self.client.post(reverse('delete_transaction', args=[other_transaction.id])).status_code,
            404,
        )
        self.assertTrue(Transaction.objects.filter(pk=other_transaction.pk).exists())

    def test_finance_crud_is_scoped_to_the_authenticated_user(self):
        owner = get_user_model().objects.create_user(username='finance-owner', password='password')
        other_user = get_user_model().objects.create_user(username='finance-other', password='password')
        anonymous_response = self.client.get(reverse('finance:entity_list', args=['contas']))
        self.assertRedirects(
            anonymous_response,
            f"{reverse('users:login')}?next={reverse('finance:entity_list', args=['contas'])}",
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse('finance:entity_create', args=['contas']),
            {
                'name': 'Conta principal',
                'account_type': Account.CHECKING,
                'opening_balance': '250.00',
                'allow_overdraft': '',
            },
        )
        self.assertRedirects(response, reverse('finance:entity_list', args=['contas']))
        account = Account.objects.get(user=owner, name='Conta principal')
        private_account = Account.objects.create(user=other_user, name='Conta privada')

        self.assertEqual(
            self.client.get(reverse('finance:entity_update', args=['contas', private_account.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse('finance:entity_delete', args=['contas', private_account.pk])).status_code,
            404,
        )
        listing = self.client.get(reverse('finance:entity_list', args=['contas']))
        self.assertContains(listing, account.name)
        self.assertNotContains(listing, private_account.name)

    def test_transaction_form_rejects_another_users_account(self):
        owner = get_user_model().objects.create_user(username='transaction-owner', password='password')
        other_user = get_user_model().objects.create_user(username='transaction-other', password='password')
        private_account = Account.objects.create(user=other_user, name='Conta de terceiro')
        self.client.force_login(owner)

        response = self.client.post(
            reverse('finance:entity_create', args=['movimentacoes']),
            {
                'description': 'Tentativa inválida',
                'amount': '10.00',
                'kind': Transaction.EXPENSE,
                'category': 'Geral',
                'category_item': '',
                'account': private_account.pk,
                'credit_card': '',
                'occurred_at': localdate().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=owner).exists())

    def test_category_card_budget_and_transaction_crud(self):
        owner = get_user_model().objects.create_user(username='crud-owner', password='password')
        self.client.force_login(owner)

        response = self.client.post(
            reverse('finance:entity_create', args=['categorias']),
            {'name': 'Geral', 'kind': Category.BOTH, 'color': '#123456'},
        )
        self.assertRedirects(response, reverse('finance:entity_list', args=['categorias']))
        category = Category.objects.get(user=owner, name='Geral')

        response = self.client.post(
            reverse('finance:entity_create', args=['cartoes']),
            {'name': 'Cartão pessoal', 'credit_limit': '1000.00', 'billing_day': '10', 'due_day': '20'},
        )
        self.assertRedirects(response, reverse('finance:entity_list', args=['cartoes']))
        card = CreditCard.objects.get(user=owner, name='Cartão pessoal')
        response = self.client.post(
            reverse('finance:entity_update', args=['cartoes', card.pk]),
            {'name': 'Cartão principal', 'credit_limit': '1200.00', 'billing_day': '10', 'due_day': '20'},
        )
        self.assertRedirects(response, reverse('finance:entity_list', args=['cartoes']))
        card.refresh_from_db()
        self.assertEqual(card.credit_limit, Decimal('1200.00'))

        response = self.client.post(
            reverse('finance:entity_create', args=['orcamentos']),
            {
                'category': category.pk,
                'amount_limit': '500.00',
                'start_date': '2026-10-01',
                'end_date': '2026-10-31',
            },
        )
        self.assertRedirects(response, reverse('finance:entity_list', args=['orcamentos']))
        budget = Budget.objects.get(user=owner, category=category)
        response = self.client.post(
            reverse('finance:entity_update', args=['orcamentos', budget.pk]),
            {
                'category': category.pk,
                'amount_limit': '650.00',
                'start_date': '2026-10-01',
                'end_date': '2026-10-31',
            },
        )
        self.assertRedirects(response, reverse('finance:entity_list', args=['orcamentos']))
        budget.refresh_from_db()
        self.assertEqual(budget.amount_limit, Decimal('650.00'))

        response = self.client.post(
            reverse('finance:entity_create', args=['movimentacoes']),
            {
                'description': 'Receita',
                'amount': '50.00',
                'kind': Transaction.INCOME,
                'category': 'Geral',
                'category_item': category.pk,
                'account': '',
                'credit_card': '',
                'occurred_at': localdate().isoformat(),
            },
        )
        self.assertRedirects(response, reverse('finance:entity_list', args=['movimentacoes']))
        transaction = Transaction.objects.get(user=owner, description='Receita')
        response = self.client.post(reverse('finance:entity_delete', args=['movimentacoes', transaction.pk]))
        self.assertRedirects(response, reverse('finance:entity_list', args=['movimentacoes']))
        self.assertFalse(Transaction.objects.filter(pk=transaction.pk).exists())

        self.client.post(reverse('finance:entity_delete', args=['orcamentos', budget.pk]))
        self.client.post(reverse('finance:entity_delete', args=['cartoes', card.pk]))
        self.client.post(reverse('finance:entity_delete', args=['categorias', category.pk]))
        self.assertFalse(Budget.objects.filter(pk=budget.pk).exists())
        self.assertFalse(CreditCard.objects.filter(pk=card.pk).exists())
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_transaction_cannot_overdraw_an_account(self):
        owner = get_user_model().objects.create_user(username='balance-owner', password='password')
        account = Account.objects.create(user=owner, name='Conta', opening_balance=Decimal('100.00'))
        self.client.force_login(owner)

        response = self.client.post(
            reverse('finance:entity_create', args=['movimentacoes']),
            {
                'description': 'Compra acima do saldo',
                'amount': '150.00',
                'kind': Transaction.EXPENSE,
                'category': 'Geral',
                'category_item': '',
                'account': account.pk,
                'credit_card': '',
                'occurred_at': '2026-09-12',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=owner).exists())
        self.assertContains(response, 'A saída excede o saldo disponível na conta.')

    def test_card_limit_and_budget_date_range_are_validated(self):
        owner = get_user_model().objects.create_user(username='limits-owner', password='password')
        category = Category.objects.create(user=owner, name='Compras', kind=Category.EXPENSE)
        card = CreditCard.objects.create(
            user=owner,
            name='Cartão limitado',
            credit_limit=Decimal('25.00'),
            billing_day=10,
            due_day=20,
        )
        self.client.force_login(owner)

        transaction_response = self.client.post(
            reverse('finance:entity_create', args=['movimentacoes']),
            {
                'description': 'Compra acima do limite',
                'amount': '30.00',
                'kind': Transaction.EXPENSE,
                'category': category.name,
                'category_item': category.pk,
                'account': '',
                'credit_card': card.pk,
                'occurred_at': localdate().isoformat(),
            },
        )
        self.assertEqual(transaction_response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=owner).exists())
        self.assertContains(transaction_response, 'A compra excede o limite disponível no cartão.')

        budget_response = self.client.post(
            reverse('finance:entity_create', args=['orcamentos']),
            {
                'category': category.pk,
                'amount_limit': '100.00',
                'start_date': '2026-10-31',
                'end_date': '2026-10-01',
            },
        )
        self.assertEqual(budget_response.status_code, 200)
        self.assertFalse(Budget.objects.filter(user=owner).exists())