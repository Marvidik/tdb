from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, UserAccount
from .utils import generate_account_number

@receiver(post_save, sender=CustomUser)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        # Generate unique account number
        account_number = generate_account_number()
        while UserAccount.objects.filter(account_number=account_number).exists():
            account_number = generate_account_number()

        UserAccount.objects.create(user=instance, account_number=account_number)
