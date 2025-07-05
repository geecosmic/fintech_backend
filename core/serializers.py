from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserWallet, Transaction

class WalletSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = UserWallet
        fields = ['user', 'balance']


class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'
