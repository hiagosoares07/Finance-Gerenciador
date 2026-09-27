from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.html import strip_tags
from django.utils.http import url_has_allowed_host_and_scheme

User = get_user_model()


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        full_name = strip_tags(request.POST.get('full_name', '').strip())
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        errors = []

        if not full_name:
            errors.append('Informe seu nome completo.')
        if not email:
            errors.append('Informe um e-mail válido.')
        elif User.objects.filter(email__iexact=email).exists():
            errors.append('Este e-mail já está cadastrado.')
        try:
            validate_password(password)
        except ValidationError as error:
            errors.extend(error.messages)

        if not errors:
            first_name, _, last_name = full_name.partition(' ')
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            login(request, user)
            return redirect('home')

        for error in errors:
            messages.error(request, error)

    return render(request, 'users/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '')
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect('home')
        messages.error(request, 'E-mail ou senha incorretos.')

    return render(request, 'users/login.html')