from django.contrib import admin
from .models import CustomUser, UserAccount, DomesticTransfer, InterBankTransfer, WireTransfer
# Register your models here.


admin.site.register(CustomUser)
admin.site.register(UserAccount)
admin.site.register(DomesticTransfer)
admin.site.register(InterBankTransfer)
admin.site.register(WireTransfer)