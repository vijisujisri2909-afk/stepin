from django.urls import path
from . import views

urlpatterns = [
    path('api/products/', views.product_list, name='product_list'),
    path('api/create-order/', views.create_order, name='api_create_order'),
    path('api/verify-payment/', views.verify_payment, name='api_verify_payment'),
    path('', views.home, name='home'),  # ithu than main
    path('home/', views.home, name='home_page'),
    path('checkout/', views.checkout, name='checkout'),
    path('account/login/', views.account_login, name='account_login'),
    path('account/register/', views.account_register, name='account_register'),
    path('account/logout/', views.account_logout, name='account_logout'),
    path('orders/', views.my_orders, name='my_orders'),
    path('api/orders/', views.orders_api, name='orders_api'),
    path('payments/razorpay/create-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('payments/razorpay/verify/', views.verify_payment, name='verify_payment'),
    path('payments/success/', views.payment_success_page, name='payment_success'),
    path('track/<int:order_id>/', views.track_order, name='track_order'),
    path('success/', views.payment_success, name='success'),
    path('create-order/', views.create_razorpay_order, name='create_order'),
    path('payment-success/', views.payment_success, name='payment_success_api'),
]
