from django.contrib import admin
from .models import UserWallet

@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

# @admin.register(DataPlan)
# class DataPlanAdmin(admin.ModelAdmin):
#     list_display = ('network', 'name', 'code', 'price')
#     search_fields = ('network', 'name', 'code')
#     list_filter = ('network',)


from .models import CablePackage

@admin.register(CablePackage)
class CablePackageAdmin(admin.ModelAdmin):
    list_display = ('provider', 'name', 'code', 'amount')
    list_filter = ('provider',)
    search_fields = ('name', 'code')