from django.urls import path
from .views import register
from .import views
from rest_framework.authtoken.views import obtain_auth_token
from .views import Home,RequestPasswordResetView,PasswordResetConfirmView,withdraw_funds,get_electricity_providers,verify_meter_number,verify_smartcard,EditProfileAPIView,flutterwave_webhook,TransactionHistoryView,FundWalletView,list_data_plans,user_dashboard,CustomLoginView,buy_electricity,CableTVPurchaseView,AirtimePurchaseView,DataPurchaseView,get_or_create_virtual_account




    
    

urlpatterns = [
    path('', Home.as_view(), name='home'),

    path('register/', register),
    path('login/', CustomLoginView.as_view(), name='login'),
    # path('api/request-password-reset/', RequestPasswordResetView.as_view()),
    path('auth/request-password-reset/', RequestPasswordResetView.as_view(), name='request-password-reset'),
    path('auth/password-reset/', PasswordResetConfirmView.as_view(), name='password-reset'),



    path('profile/edit/', EditProfileAPIView.as_view(), name='edit-profile'),


   

    path('fund-wallet/', FundWalletView.as_view(), name='fund-wallet'),
    path('virtual-account/', get_or_create_virtual_account, name='get-virtual-account'),
    path('transactions/', TransactionHistoryView.as_view(), name='transaction-history'),

    path('flutterwave/webhook/', flutterwave_webhook, name='flutterwave-webhook'),

    

    # 🔵 Airtime-related endpoint (if implemented)
    path('airtime/purchase/', AirtimePurchaseView.as_view(), name='airtime-purchase'),
    # path('data/', DataPurchaseView.as_view(), name='data-purchase'),

    path('data/purchase/', DataPurchaseView.as_view(), name='data-purchase'),
    # path("cable-packages/", CablePackageListView.as_view()),

    
    path('cable/', CableTVPurchaseView.as_view(), name='cable-tv-purchase'),
    path('cable-packages/', views.cable_packages),
    path("cable/verify/", verify_smartcard),
    path("cable/saved/", views.get_saved_smartcards),




    # path("cable-packages/", CablePackageListView.as_view(), name="cable-packages"),


    path('electricity/', buy_electricity, name='buy_electricity'),
    path('electricity/verify/', verify_meter_number, name='verify-meter'),
    path('electricity/providers/', get_electricity_providers),


    
    # path('wallet/balance/', WalletBalanceView.as_view(), name='wallet-balance'),

    path('dashboard/', user_dashboard, name='user-dashboard'),
    path("data-plans/", list_data_plans),


    path('withdraw/', withdraw_funds, name='withdraw_funds'),

]