from urllib.parse import urlencode

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

def home(request):
    # Simple data - Product model thevai illa
    products = [
        {'name': 'Red High Heel', 'price': 1999, 'image': '/media/images/red.jpg'},
        {'name': 'Blue Heel', 'price': 2499, 'image': '/media/images/blue.jpg'},
        {'name': 'Brown Loafer', 'price': 2999, 'image': '/media/images/men1.jpg'},
    ]
    return render(request, 'home.html', {'products': products})


def _render_auth_page(request, *, tab='login', error=''):
    return render(request, 'home.html', {
        'active_page': 'login',
        'active_auth_tab': tab,
        'auth_error': error,
    })


def account_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'GET':
        tab = request.GET.get('tab', 'login')
        return _render_auth_page(request, tab=tab if tab in {'login', 'register'} else 'login')

    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    if not email or not password:
        return _render_auth_page(request, error='Enter your email and password.')

    user_record = User.objects.filter(email__iexact=email).first()
    user = authenticate(request, username=user_record.username, password=password) if user_record else None
    if user is None:
        return _render_auth_page(request, error='The email or password is incorrect.')

    login(request, user)
    destination = request.POST.get('next', '')
    if destination and url_has_allowed_host_and_scheme(destination, {request.get_host()}):
        return redirect(destination)
    return redirect('home')


def account_register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method != 'POST':
        return redirect(f"/account/login/?{urlencode({'tab': 'register'})}")

    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')

    if not name or not email or not password or not confirm_password:
        return _render_auth_page(request, tab='register', error='Complete every field.')
    try:
        validate_email(email)
    except ValidationError:
        return _render_auth_page(request, tab='register', error='Enter a valid email address.')
    if User.objects.filter(email__iexact=email).exists():
        return _render_auth_page(request, tab='register', error='An account with this email already exists.')
    if password != confirm_password:
        return _render_auth_page(request, tab='register', error='The passwords do not match.')

    user = User(username=email, email=email, first_name=name[:150])
    try:
        validate_password(password, user=user)
    except ValidationError as error:
        return _render_auth_page(request, tab='register', error=' '.join(error.messages))

    user.set_password(password)
    user.save()
    login(request, user)
    return redirect('home')


def account_logout(request):
    if request.method != 'POST':
        return redirect('home')
    logout(request)
    return redirect('home')