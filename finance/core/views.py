from calendar import Calendar
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import strip_tags
from django.utils.timezone import localdate

from users.models import Transaction


def home(request):
    if request.user.is_authenticated:
        return dashboard(request)
    return render(request, 'home.html')


@login_required
def dashboard(request):
    today = localdate()
    month_start = today.replace(day=1)
    transactions = Transaction.objects.filter(user=request.user)
    month_transactions = transactions.filter(occurred_at__gte=month_start, occurred_at__lte=today)
    income_total = month_transactions.filter(kind=Transaction.INCOME).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    expense_total = month_transactions.filter(kind=Transaction.EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    all_income = transactions.filter(kind=Transaction.INCOME).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    all_expense = transactions.filter(kind=Transaction.EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    daily_totals = {
        item['occurred_at'].day: item['total']
        for item in month_transactions.values('occurred_at').annotate(total=Sum('amount'))
    }
    calendar_weeks = Calendar(firstweekday=0).monthdayscalendar(today.year, today.month)
    max_month_total = max(income_total, expense_total)
    month_names = [
        'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
    ]

    context = {
        'transactions': transactions[:8],
        'balance': all_income - all_expense,
        'income_total': income_total,
        'expense_total': expense_total,
        'net_total': income_total - expense_total,
        'income_width': int(income_total * 100 / max_month_total) if max_month_total else 0,
        'expense_width': int(expense_total * 100 / max_month_total) if max_month_total else 0,
        'calendar_weeks': calendar_weeks,
        'weekdays': ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
        'daily_totals': daily_totals,
        'month_label': f'{month_names[today.month - 1]} de {today.year}',
        'today': today,
        'has_transactions': transactions.exists(),
    }
    return render(request, 'dashboard.html', context)


@login_required
def add_transaction(request):
    if request.method == 'POST':
        description = strip_tags(request.POST.get('description', '').strip())
        category = strip_tags(request.POST.get('category', '').strip()) or 'Geral'
        kind = request.POST.get('kind', '')
        raw_amount = request.POST.get('amount', '').replace(',', '.')
        raw_date = request.POST.get('occurred_at', '')

        try:
            amount = Decimal(raw_amount)
            occurred_at = date.fromisoformat(raw_date)
            if amount <= 0 or amount.as_tuple().exponent < -2:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, 'Informe um valor positivo com até duas casas decimais e uma data válida.')
            return redirect('home')

        if not description or kind not in (Transaction.INCOME, Transaction.EXPENSE):
            messages.error(request, 'Preencha a descrição e escolha entrada ou saída.')
            return redirect('home')

        Transaction.objects.create(
            user=request.user,
            description=description,
            amount=amount,
            kind=kind,
            category=category[:40],
            occurred_at=occurred_at,
        )
        messages.success(request, 'Movimentação adicionada.')
    return redirect('home')


@login_required
def delete_transaction(request, transaction_id):
    if request.method == 'POST':
        transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)
        transaction.delete()
        messages.success(request, 'Movimentação removida.')
    return redirect('home')


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('users:login')