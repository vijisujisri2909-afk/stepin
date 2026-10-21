from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # ithu than main
    path('home/', views.home, name='home_page'),
    path('account/login/', views.account_login, name='account_login'),
    path('account/register/', views.account_register, name='account_register'),
    path('account/logout/', views.account_logout, name='account_logout'),
]