from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.financial_forms import AccountForm, BudgetForm, CategoryForm, CreditCardForm, TransactionForm
from users.models import Account, Budget, Category, CreditCard, Transaction


ENTITIES = {
    'categorias': (Category, CategoryForm, 'Categorias', 'Categoria'),
    'contas': (Account, AccountForm, 'Contas', 'Conta'),
    'cartoes': (CreditCard, CreditCardForm, 'Cartões', 'Cartão'),
    'orcamentos': (Budget, BudgetForm, 'Orçamentos', 'Orçamento'),
    'movimentacoes': (Transaction, TransactionForm, 'Movimentações', 'Movimentação'),
}


def get_entity(entity):
    try:
        return ENTITIES[entity]
    except KeyError as error:
        raise Http404('Seção financeira não encontrada.') from error


def persist_form(form, user):
    instance = form.save(commit=False)
    try:
        with transaction.atomic():
            if isinstance(instance, Transaction):
                for field_name, model in (('account', Account), ('credit_card', CreditCard)):
                    related_id = getattr(instance, f'{field_name}_id')
                    if related_id:
                        try:
                            related_object = model.objects.select_for_update().get(pk=related_id, user=user)
                        except model.DoesNotExist:
                            form.add_error(field_name, 'Este recurso financeiro não está mais disponível para sua conta.')
                            return False
                        setattr(instance, field_name, related_object)
            elif isinstance(instance, (Account, CreditCard)) and instance.pk:
                instance.__class__.objects.select_for_update().get(pk=instance.pk, user=user)

            instance.full_clean()
            instance.save()
            form.save_m2m()
    except ValidationError as error:
        if error.message_dict:
            for field_name, field_errors in error.message_dict.items():
                form.add_error(field_name if field_name in form.fields else None, field_errors)
        else:
            form.add_error(None, error.messages)
        return False
    return True


@login_required(login_url='users:login')
def entity_list(request, entity):
    model, _, title, _ = get_entity(entity)
    objects = model.objects.filter(user=request.user)
    if model is Transaction:
        start_date = request.GET.get('inicio')
        end_date = request.GET.get('fim')
        category_id = request.GET.get('categoria')
        kind = request.GET.get('tipo')
        try:
            if start_date:
                objects = objects.filter(occurred_at__gte=date.fromisoformat(start_date))
            if end_date:
                objects = objects.filter(occurred_at__lte=date.fromisoformat(end_date))
        except ValueError:
            messages.error(request, 'Informe um período válido.')
        if category_id and category_id.isdecimal():
            objects = objects.filter(category_item_id=category_id, category_item__user=request.user)
        if kind in (Transaction.INCOME, Transaction.EXPENSE):
            objects = objects.filter(kind=kind)

    return render(request, 'finance/entity_list.html', {
        'entity': entity,
        'title': title,
        'objects': objects,
        'categories': Category.objects.filter(user=request.user),
        'is_transaction_list': model is Transaction,
    })


@login_required(login_url='users:login')
def entity_create(request, entity):
    _, form_class, title, singular = get_entity(entity)
    form = form_class(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid() and persist_form(form, request.user):
        messages.success(request, f'{singular} salvo com sucesso.')
        return redirect('finance:entity_list', entity=entity)
    return render(request, 'finance/entity_form.html', {
        'entity': entity,
        'title': title,
        'form': form,
        'is_edit': False,
    })


@login_required(login_url='users:login')
def entity_update(request, entity, pk):
    model, form_class, title, _ = get_entity(entity)
    instance = get_object_or_404(model, pk=pk, user=request.user)
    form = form_class(request.POST or None, instance=instance, user=request.user)
    if request.method == 'POST' and form.is_valid() and persist_form(form, request.user):
        messages.success(request, 'Alterações salvas com sucesso.')
        return redirect('finance:entity_list', entity=entity)
    return render(request, 'finance/entity_form.html', {
        'entity': entity,
        'title': title,
        'form': form,
        'is_edit': True,
    })


@login_required(login_url='users:login')
@require_POST
def entity_delete(request, entity, pk):
    model, _, _, singular = get_entity(entity)
    instance = get_object_or_404(model, pk=pk, user=request.user)
    try:
        instance.delete()
    except ProtectedError:
        messages.error(request, 'Não é possível excluir esta categoria enquanto houver orçamentos vinculados.')
    else:
        messages.success(request, f'{singular} removido com sucesso.')
    return redirect('finance:entity_list', entity=entity)
