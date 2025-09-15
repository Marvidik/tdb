# accounts/urls.py
from django.urls import path
from .views import create_account,login_account,account_statement,make_domestic_transfer,make_interbank_transfer,make_wire_transfer

urlpatterns = [
    path("register/", create_account, name="create_account"),
    path("login/", login_account, name="login_account"),

    path('account/statement/', account_statement, name='account-statement'),
    path('domestic/transfer/',  make_domestic_transfer, name='wire-transfer'),
    path('interbank/transfer/', make_interbank_transfer, name='interbank-transfer'),
    path('wire/transfer/', make_wire_transfer, name='wire-transfer'),
    
]
