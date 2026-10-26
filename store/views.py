import json
import logging
import os

from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
import razorpay

from .models import Order, Product

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'home.html', {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    })

# Page kaamikura view - ITHU THAAN MUKKIYAM
def checkout_page(request):
    return render(request, 'checkout.html')

def checkout(request):
    print("Checkout page called")
    return render(request, 'checkout.html')

def product_list(request):
    products = Product.objects.all().values('id', 'name', 'price', 'image', 'brand', 'stock')
    return JsonResponse({'products': list(products)})


@csrf_exempt
def create_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed, use POST'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        amount = int(payload.get('amount', 0))
        payment_method = str(payload.get('payment_method', '')).strip().upper()
        if amount <= 0:
            return JsonResponse({'error': 'Amount must be greater than zero.'}, status=400)
        if payment_method not in {'COD', 'RAZORPAY'}:
            return JsonResponse({'error': 'payment_method must be COD or RAZORPAY.'}, status=400)

        customer_name = str(payload.get('customer_name', '')).strip()
        product_name = str(payload.get('product_name', '')).strip()

        if payment_method == 'COD':
            order = Order.objects.create(
                product_name=product_name,
                amount=amount,
                payment_method='COD',
                customer_name=customer_name,
                status='pending',
            )
            print(f"COD order created: database_id={order.id}, amount={amount}")
            logger.info("COD order created: database_id=%s amount=%s", order.id, amount)
            return JsonResponse({'success': True, 'order_id': str(order.id), 'amount': amount})

        key_id = os.environ.get('RAZORPAY_KEY_ID')
        key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
        if not key_id or not key_secret:
            message = 'Set RAZORPAY_KEY_SECRET in Render Env'
            print(f"Razorpay configuration error: {message}")
            logger.error("Razorpay configuration is missing RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET")
            return JsonResponse({'success': False, 'error': message}, status=503)

        print(f"Creating Razorpay order: amount={amount}, key_id={key_id[:8]}...")
        client = razorpay.Client(auth=(key_id, key_secret))
        razorpay_order = client.order.create({
            'amount': amount,
            'currency': 'INR',
            'payment_capture': 1,
        })
        order = Order.objects.create(
            product_name=product_name,
            amount=amount,
            payment_method='RAZORPAY',
            payment_id=str(razorpay_order['id']),
            customer_name=customer_name,
            status='created',
        )
        print(f"Razorpay order created: razorpay_id={razorpay_order['id']}")
        logger.info("Razorpay order created: razorpay_id=%s database_id=%s", razorpay_order['id'], order.id)
        return JsonResponse({
            'success': True,
            'order_id': razorpay_order['id'],
            'amount': amount,
            'currency': 'INR',
            'key_id': key_id,
        })
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"Invalid create-order payload: {error}")
        logger.warning("Invalid create-order payload: %s", error)
        return JsonResponse({'success': False, 'error': 'Invalid order payload.'}, status=400)
    except Exception as error:
        print(f"Razorpay order creation failed: {error}")
        logger.exception("Order creation failed")
        return JsonResponse({'success': False, 'error': f'Could not create Razorpay order: {error}'}, status=502)

def create_razorpay_order(request):
    return create_order(request)

def verify_payment(request):
    if request.method != 'POST':
        return HttpResponse('Method not allowed, use POST', status=405)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.utility.verify_payment_signature({
            'razorpay_order_id': str(payload['razorpay_order_id']),
            'razorpay_payment_id': str(payload['razorpay_payment_id']),
            'razorpay_signature': str(payload['razorpay_signature']),
        })
        return JsonResponse({'success': True})
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Incomplete payment details.'}, status=400)
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({'success': False, 'error': 'Payment signature verification failed.'}, status=400)
    except Exception as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)

def payment_success(request):
    return render(request, 'success.html', {'reference': request.GET.get('reference', '')})

def payment_success_page(request):
    return payment_success(request)

def account_login(request):
    if request.method == 'GET':
        return render(request, 'home.html', {'active_page': 'login', 'razorpay_key_id': settings.RAZORPAY_KEY_ID})
    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    user_record = User.objects.filter(email__iexact=email).first()
    user = authenticate(request, username=user_record.username, password=password) if user_record else None
    if user is None:
        return render(request, 'home.html', {
            'active_page': 'login', 'active_auth_tab': 'login',
            'auth_error': 'The email or password is incorrect.',
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        })
    login(request, user)
    return redirect('home')

def account_register(request):
    if request.method != 'POST':
        return render(request, 'home.html', {'active_page': 'login', 'active_auth_tab': 'register', 'razorpay_key_id': settings.RAZORPAY_KEY_ID})
    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    if password != request.POST.get('confirm_password', ''):
        return render(request, 'home.html', {'active_page': 'login', 'active_auth_tab': 'register', 'auth_error': 'The passwords do not match.', 'razorpay_key_id': settings.RAZORPAY_KEY_ID})
    user = User.objects.create_user(username=email, email=email, password=password, first_name=request.POST.get('name', '').strip())
    login(request, user)
    return redirect('home')

def account_logout(request):
    logout(request)
    return redirect('home')
