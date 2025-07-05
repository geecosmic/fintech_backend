from django.db import models
from django.contrib.auth.models import User

class UserWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - ₦{self.balance}"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('fund', 'Fund Wallet'),
        ('airtime', 'Airtime Purchase'),
        ('data', 'Data Purchase'),
        ('electricity', 'Electricity Bill'),
        ('cable', 'Cable TV Payment'),
        ('withdraw', 'Withdraw'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    txn_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')  # pending, success, failed
    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    meta = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.txn_type} - ₦{self.amount}"




class VirtualAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, unique=True)
    bank_name = models.CharField(max_length=100)
    provider_ref = models.CharField(max_length=100)  # from Monnify or provider

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"
    

# -------------BUY ELECTRICITY--------------------------------------------------------

class ElectricityTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    disco = models.CharField(max_length=10)  # e.g. "01"
    meter_no = models.CharField(max_length=20)
    meter_type = models.CharField(max_length=10)  # "01" or "02"
    phone = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default="PENDING")
    token = models.TextField(blank=True)
    response_log = models.TextField(blank=True)  # ✅ new field
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.order_id}"


# core/models.py
# class ElectricityTransaction(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     order_id = models.CharField(max_length=100, blank=True)
#     request_id = models.CharField(max_length=100, blank=True)
#     disco = models.CharField(max_length=10)  # e.g. "01"
#     meter_no = models.CharField(max_length=20)
#     meter_type = models.CharField(max_length=10)  # "01" or "02"
#     phone = models.CharField(max_length=15)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     status = models.CharField(max_length=50, default="PENDING")
#     token = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user.username} - {self.order_id}"



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True)

    def __str__(self):
        return self.user.username
    

# ------------------------CABLE PAYMENT------------------------------------------


class CablePackage(models.Model):
    PROVIDERS = [
        ('dstv', 'DSTV'),
        ('gotv', 'GOTV'),
        ('startimes', 'Startimes'),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDERS)
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    amount = models.IntegerField()

    meta = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.provider})"
    

# models.py
class SmartcardHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)  # 'dstv', 'gotv', 'startimes'
    smartcard = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=100)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'provider', 'smartcard')

    def __str__(self):
        return f"{self.provider.upper()} - {self.smartcard} ({self.customer_name})"    




