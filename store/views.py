import json
import secrets
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import razorpay
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from .models import PaymentOrder

def home(request):
    # Simple data - Product model thevai illa
    products = [
        {'name': 'Red High Heel', 'price': 1999, 'image': '/media/images/red.jpg'},
        {'name': 'Blue Heel', 'price': 2499, 'image': '/media/images/blue.jpg'},
        {'name': 'Brown Loafer', 'price': 2999, 'image': '/media/images/men1.jpg'},
    ]
    return render(request, 'home.html', {
        'products': products,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    })


def _render_auth_page(request, *, tab='login', error=''):
    return render(request, 'home.html', {
        'active_page': 'login',
        'active_auth_tab': tab,
        'auth_error': error,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    })


def _parse_payment_request(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError('The payment request is not valid JSON.')

    items = payload.get('items')
    customer = payload.get('customer') or {}
    if not isinstance(items, list) or not items:
        raise ValueError('Your cart is empty.')
    if not isinstance(customer, dict):
        raise ValueError('Customer details are invalid.')

    normalized_items = []
    total = Decimal('0')
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('A cart item is invalid.')
        try:
            price = Decimal(str(item['price']))
            quantity = int(item['quantity'])
        except (KeyError, InvalidOperation, TypeError, ValueError):
            raise ValueError('A cart item has an invalid price or quantity.')
        if price <= 0 or quantity < 1 or quantity > 10:
            raise ValueError('A cart item has an invalid price or quantity.')
        title = str(item.get('title', '')).strip()
        image = str(item.get('image', '')).strip()
        if not title or not image:
            raise ValueError('A cart item is missing its product details.')
        normalized_items.append({
            'title': title,
            'image': image,
            'price': float(price),
            'size': str(item.get('size', '41')),
            'quantity': quantity,
        })
        total += price * quantity

    amount_paise = int((total * 100).quantize(Decimal('1')))
    if amount_paise < 100:
        raise ValueError('The payment amount must be at least ₹1.')
    return normalized_items, customer, amount_paise


@require_POST
def create_razorpay_order(request):
    try:
        items, customer, amount_paise = _parse_payment_request(request)
        client = razorpay.Client({
            'key_id': settings.RAZORPAY_KEY_ID,
            'key_secret': settings.RAZORPAY_KEY_SECRET,
        })
        razorpay_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f"stepup_{secrets.token_hex(8)}",
            'notes': {'store': 'StepUp.in'},
        })
        reference = f"STEPUP-{secrets.token_hex(6).upper()}"
        PaymentOrder.objects.create(
            reference=reference,
            razorpay_order_id=razorpay_order['id'],
            amount=amount_paise,
            currency='INR',
            items=items,
            customer=customer,
        )
        return JsonResponse({
            'key_id': settings.RAZORPAY_KEY_ID,
            'order_id': razorpay_order['id'],
            'amount': amount_paise,
            'currency': 'INR',
            'reference': reference,
        })
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    except Exception:
        return JsonResponse(
            {'error': 'Razorpay could not create the order. Check the test credentials and try again.'},
            status=502,
        )


@require_POST
def verify_payment(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        order_id = str(payload['razorpay_order_id'])
        payment_id = str(payload['razorpay_payment_id'])
        signature = str(payload['razorpay_signature'])
        payment_order = PaymentOrder.objects.get(razorpay_order_id=order_id)
        client = razorpay.Client({
            'key_id': settings.RAZORPAY_KEY_ID,
            'key_secret': settings.RAZORPAY_KEY_SECRET,
        })
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature,
        })
        payment_order.razorpay_payment_id = payment_id
        payment_order.status = PaymentOrder.Status.PAID
        payment_order.paid_at = timezone.now()
        payment_order.save(update_fields=['razorpay_payment_id', 'status', 'paid_at'])
        return JsonResponse({'success': True, 'reference': payment_order.reference})
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, PaymentOrder.DoesNotExist):
        return JsonResponse({'error': 'The payment details could not be found.'}, status=400)
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({'error': 'Payment signature verification failed.'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Payment verification failed. Please contact StepUp.in support.'}, status=502)


def payment_success(request):
    return render(request, 'payment_success.html', {
        'reference': request.GET.get('reference', ''),
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
