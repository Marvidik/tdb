from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now



# Option 1: Extend AbstractUser to include all fields
class CustomUser(AbstractUser):
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        blank=True,
        null=True
    )
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ]
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )
    
    address = models.TextField(blank=True, null=True)
    
    ACCOUNT_TYPE_CHOICES = [
        ('savings', 'Savings'),
        ('current', 'Current')
    ]
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default='savings'
    )
    
    ACCOUNT_CURRENCY_CHOICES = [
        ('usd', 'Dollar'),
        ('eur', 'Euro'),
        ('ngn', 'Naira')
    ]
    account_currency = models.CharField(
        max_length=10,
        choices=ACCOUNT_CURRENCY_CHOICES,
        default='usd'
    )

    def __str__(self):
        return f"{self.username} ({self.email})"




# Extend UserAccount to include account number
class UserAccount(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, unique=True)  # User's bank-like account number
    account_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_withdrawal = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.user.username} - {self.account_number}"

# Transaction base class
class Transaction(models.Model):
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('unknown', 'Unknown'),
    ]
    TRANSACTION_TYPE = [
        ('domestic_transfer', 'Domestic Transfer'),
        ('inter_bank', 'Inter-Bank Transfer'),
        ('wire', 'Wire Transfer'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    account = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='unknown')
    date = models.DateTimeField(default=now)

    class Meta:
        abstract = True  

# Domestic transfer
class DomesticTransfer(Transaction):
    beneficiary_name = models.CharField(max_length=100)
    beneficiary_account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, default='savings') 

    def save(self, *args, **kwargs):
        self.transaction_type = "domestic_transfer"
        super().save(*args, **kwargs)

# Inter-bank transfer (international)
class InterBankTransfer(Transaction):
    beneficiary_name = models.CharField(max_length=100)
    iban = models.CharField(max_length=34)  
    bank_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, default='savings')
    password_confirm = models.CharField(max_length=128) 
    country = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        self.transaction_type = "inter_bank"
        super().save(*args, **kwargs)

# Wire transfer
class WireTransfer(Transaction):
    beneficiary_name = models.CharField(max_length=100)
    routing_number = models.CharField(max_length=20)
    iban = models.CharField(max_length=34)
    bank_name = models.CharField(max_length=100)
    swift_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, default='savings')
    password_confirm = models.CharField(max_length=128)

    def save(self, *args, **kwargs):
        self.transaction_type = "wire"
        super().save(*args, **kwargs)
