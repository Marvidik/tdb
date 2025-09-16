import random
from django.db import models
from django.contrib.auth.models import AbstractUser

def generate_account_number():
    # Example: 10-digit numeric account number
    return str(random.randint(1000000000, 9999999999))
