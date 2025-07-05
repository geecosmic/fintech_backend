from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth.models import User
from .models import VirtualAccount, UserWallet, ElectricityTransaction
from django.db import transaction
from .serializers import TransactionSerializer  # Make sure this exists
from django.utils.dateparse import parse_date
import requests
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import UserWallet, Transaction
from .serializers import WalletSerializer
import uuid

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token


from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny

import os



class EditProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        })

    def put(self, request):
        user = request.user
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")
        email = request.data.get("email", "")

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        return Response({"message": "Profile updated successfully."})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_dashboard(request):
    user = request.user

    # Wallet
    wallet = UserWallet.objects.filter(user=user).first()
    balance = wallet.balance if wallet else 0

    # Virtual Account
    account = VirtualAccount.objects.filter(user=user).first()
    account_info = {
        "account_number": account.account_number if account else None,
        "bank_name": account.bank_name if account else None,
        "account_reference": account.provider_ref if account else None,
    }

    # Recent Transactions
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:10]
    txn_data = TransactionSerializer(transactions, many=True).data

    return Response({
        "user": user.username,  # ✅ Add this line to send the name
        "wallet_balance": balance,
        "virtual_account": account_info,
        "recent_transactions": txn_data,
    })










@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # 👈 This line fixes it!
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)

    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key})

@api_view(['POST'])
@permission_classes([AllowAny]) 
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)

    if not user:
        return Response({'error': 'Invalid credentials'}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key})





# ------------------------------WALLET BALANCE--------------------------------------



class WalletBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_id = os.getenv('CLUBKONNECT_USERID')
            api_key = os.getenv('CLUBKONNECT_APIKEY')
            url = f"https://www.nellobytesystems.com/APIWalletBalanceV1.asp?UserID={user_id}&APIKey={api_key}"
            response = requests.get(url)
            data = response.json()

            if 'balance' in data:
                return Response({'balance': data['balance']}, status=200)
            else:
                return Response({'error': 'Failed to fetch balance'}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        






# --------------------------------------------------------------------------------------

class CustomLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data['token'])
        user = token.user
        return Response({
            'token': token.key,
            'username': user.username,
            'email': user.email,
        })






# -------------------------FUND WALLET--------------------------------

from decimal import Decimal

class FundWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get("amount")
        if not amount:
            return Response({"error": "Amount is required"}, status=400)

        try:
            amount_decimal = Decimal(str(amount))
        except:
            return Response({"error": "Invalid amount format"}, status=400)

        wallet, _ = UserWallet.objects.get_or_create(user=request.user)
        wallet.balance += amount_decimal
        wallet.save()

        Transaction.objects.create(
            user=request.user,
            amount=amount_decimal,
            txn_type='fund',
            status='success',
            reference=str(uuid.uuid4())
        )

        return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)
    



    # ------------------------ VIRTUAL ACCOUNt----------------------------


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_or_create_virtual_account(request):
    user = request.user

    try:
        account = VirtualAccount.objects.get(user=user)
    except VirtualAccount.DoesNotExist:
        try:
            with transaction.atomic():
                # ✅ Create Flutterwave Virtual Account
                url = "https://api.flutterwave.com/v3/virtual-account-numbers"
                # headers = {
                #     "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
                #     "Content-Type": "application/json"
                # }

                headers = {
                    "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "email": user.email,
                    "is_permanent": True,
                    "tx_ref": f"{user.username}-wallet-{uuid.uuid4()}",
                    "narration": f"{user.get_full_name()} Wallet",
                    "amount": 100,  # Required by Flutterwave, just dummy
                    "currency": "NGN",
                    "duration": 0
                }

                response = requests.post(url, headers=headers, json=payload)
                res_json = response.json()

                if res_json.get("status") != "success":
                    return Response({"error": "Failed to create Flutterwave virtual account", "raw": res_json}, status=502)

                acct_data = res_json["data"]
                account = VirtualAccount.objects.create(
                    user=user,
                    account_number=acct_data["account_number"],
                    bank_name=acct_data["bank_name"],
                    provider_ref=acct_data["order_ref"]
                )
                UserWallet.objects.get_or_create(user=user)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    wallet = UserWallet.objects.get(user=user)

    return Response({
        "wallet_balance": wallet.balance,
        "account_number": account.account_number,
        "bank_name": account.bank_name,
        "account_reference": account.provider_ref,
    }, status=status.HTTP_200_OK)








@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw_funds(request):
    user = request.user
    amount = Decimal(request.data.get("amount", "0"))
    bank_code = request.data.get("bank_code")
    account_number = request.data.get("account_number")
    account_name = request.data.get("account_name")  # Optional

    if not (amount and bank_code and account_number):
        return Response({"error": "Missing fields"}, status=400)

    if amount <= 0:
        return Response({"error": "Invalid amount"}, status=400)

    wallet = UserWallet.objects.get(user=user)

    if wallet.balance < amount:
        return Response({"error": "Insufficient wallet balance"}, status=400)

    # Deduct first to prevent race conditions
    wallet.balance -= amount
    wallet.save()

    # Generate transaction reference
    reference = f"{user.username}-withdraw-{uuid.uuid4()}"

    # Call Flutterwave Transfer API
    transfer_url = "https://api.flutterwave.com/v3/transfers"
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "account_bank": bank_code,
        "account_number": account_number,
        "amount": float(amount),
        "narration": f"{user.username} Withdrawal",
        "currency": "NGN",
        "reference": reference,
        "callback_url": "https://yourdomain.com/webhook/flutterwave/withdrawal",
        "debit_currency": "NGN"
    }

    response = requests.post(transfer_url, headers=headers, json=payload)
    res_json = response.json()

    # Log transaction
    Transaction.objects.create(
        user=user,
        txn_type="withdraw",
        amount=amount,
        reference=reference,
        status="success" if res_json.get("status") == "success" else "failed",
        meta=res_json
    )

    if res_json.get("status") == "success":
        return Response({"message": "Withdrawal initiated", "data": res_json.get("data")}, status=200)
    else:
        # Rollback wallet balance
        wallet.balance += amount
        wallet.save()
        return Response({"error": "Withdrawal failed", "details": res_json}, status=500)










# -----------------------------TRANSACTION HISTORY--------------------------------------


class TransactionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            transactions = transactions.filter(created_at__date__gte=parse_date(start_date))
        if end_date:
            transactions = transactions.filter(created_at__date__lte=parse_date(end_date))

        transactions = transactions.order_by('-created_at')
        return Response(TransactionSerializer(transactions, many=True).data)
    


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_transactions(request):
    Transaction.objects.filter(user=request.user).delete()
    return Response(status=204)


    # ------------------------- WEBHOOK------------------------------------


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny]) 
def flutterwave_webhook(request):
    # ✅ Verify signature (security)
    signature = request.headers.get('verif-hash')
    if not signature or signature != settings.FLUTTERWAVE_SECRET_HASH:
        return Response({"error": "Invalid signature"}, status=403)

    payload = request.data
    event = payload.get('event')
    data = payload.get('data', {})

    if event == 'transfer.completed' and data.get("status") == "SUCCESSFUL":
        # ✅ Get account details
        account_number = data.get("account_number")
        amount = Decimal(data.get("amount", 0))
        reference = data.get("reference") or data.get("flw_ref")

        # ✅ Find which user this belongs to
        try:
            virtual_account = VirtualAccount.objects.get(account_number=account_number)
            wallet = UserWallet.objects.get(user=virtual_account.user)

            # Prevent duplicate
            if Transaction.objects.filter(reference=reference).exists():
                return Response({"message": "Transaction already processed"})

            # ✅ Fund Wallet
            wallet.balance += amount
            wallet.save()

            # ✅ Log transaction
            Transaction.objects.create(
                user=virtual_account.user,
                txn_type='fund',
                amount=amount,
                status='success',
                reference=reference,
                meta=payload
            )

            return Response({"message": "Wallet funded successfully"}, status=200)

        except VirtualAccount.DoesNotExist:
            return Response({"error": "Virtual account not found"}, status=404)

    return Response({"message": "Ignored"}, status=200)




from django.utils.decorators import method_decorator
from decimal import Decimal, InvalidOperation




def get_user_from_reference(reference):
    try:
        account = VirtualAccount.objects.get(provider_ref=reference)
        return account.user
    except VirtualAccount.DoesNotExist:
        return None










# ----------------------------------AIRTIME VIEW-----------------------


from .models import UserWallet, Transaction
# this 0ne

class AirtimePurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("Incoming POST:", request.data)

        amount = request.data.get('amount')
        phone = request.data.get('phone')
        network = request.data.get('network')
        user = request.user

        if not all([amount, phone, network]):
            return Response({"error": "All fields are required."}, status=400)

        try:
            amount = int(amount)
        except ValueError:
            return Response({"error": "Invalid amount format. Use whole numbers only."}, status=400)

        original_amount = amount  # amount user wants as airtime
        adjusted_amount = original_amount  # amount to deduct from wallet

        if not user.is_staff:
            # Apply discount (user gets a bonus)
            if network == "01":  # MTN
                adjusted_amount = original_amount - int(0.02 * original_amount)
            elif network == "04":  # 9mobile
                adjusted_amount = original_amount - int(0.03 * original_amount)
            elif network == "02":  # Glo
                adjusted_amount = original_amount - int(0.03 * original_amount)
            elif network == "03":  # Airtel
                adjusted_amount = original_amount - int(0.02 * original_amount)

        try:
            wallet = UserWallet.objects.get(user=user)
        except UserWallet.DoesNotExist:
            return Response({"error": "Wallet not found."}, status=404)

        if wallet.balance < Decimal(adjusted_amount):
            return Response({"error": "Insufficient wallet balance."}, status=400)

        request_id = str(uuid.uuid4())
        clubkonnect_url = "https://www.nellobytesystems.com/APIAirtimeV1.asp"
        params = {
            "UserID": settings.CLUBKONNECT_USERID,
            "APIKey": settings.CLUBKONNECT_APIKEY,
            "MobileNetwork": network,
            "Amount": str(original_amount),
            "MobileNumber": phone,
            "RequestID": request_id,
            "CallBackURL": "https://yourdomain.com/webhook/"
        }

        # Wrap in a DB transaction to ensure rollback if something fails
        with transaction.atomic():
            wallet.balance -= Decimal(adjusted_amount)
            wallet.save()
            print("✅ Deducted from wallet. New balance:", wallet.balance)

            try:
                response = requests.get(clubkonnect_url, params=params, timeout=10)
                result = response.json()

                api_status = result.get("Status") or result.get("status")
                if api_status and api_status.lower() in ["successful", "order_received"]:
                    final_status = "success"
                else:
                    raise Exception("API responded with failure")

            except Exception as e:
                wallet.balance += Decimal(adjusted_amount)
                wallet.save()
                print("❌ Error or failed response. Refunded:", adjusted_amount)
                res_data = response.json()

                Transaction.objects.create(
                    user=user,
                    txn_type='airtime',
                    amount=Decimal(adjusted_amount),
                    status="failed",
                    reference=request_id,
                    # meta={"error": str(e)}
                    meta=res_data 
                )
                return Response({"error": f"Airtime request failed: {str(e)}"}, status=500)

            # Log successful transaction
            Transaction.objects.create(
                user=user,
                txn_type='airtime',
                amount=Decimal(adjusted_amount),
                status="success",
                reference=request_id,
                meta=result
            )

        return Response({
            "message": "Airtime request sent successfully.",
            "status": "success",
            "api_response": result
        }, status=200)


# class AirtimePurchaseView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         print("Incoming POST:", request.data)

#         amount = request.data.get('amount')
#         phone = request.data.get('phone')
#         network = request.data.get('network')
#         user = request.user

#         if not all([amount, phone, network]):
#             return Response({"error": "All fields are required."}, status=400)

#         try:
#             amount = int(amount)
#         except ValueError:
#             return Response({"error": "Invalid amount format. Use whole numbers only."}, status=400)

#         # 👇 Apply markup if not admin
#         adjusted_amount = amount
#         if not user.is_staff:
            
#             if network == "01":  # MTN
#                 adjusted_amount = int(amount * 0.98)  # 2% bonus
#             elif network == "04":  # 9mobile
#                 adjusted_amount = int(amount * 0.97)  # 3% bonus
#             elif network == "02":  # Glo
#                 adjusted_amount = int(amount * 0.97)  # 3% bonus
#             elif network == "03":  # Airtel
#                 adjusted_amount = int(amount * 0.98)  # 2% bonus


#         try:
#             wallet = UserWallet.objects.get(user=user)
#         except UserWallet.DoesNotExist:
#             return Response({"error": "Wallet not found."}, status=404)

#         if wallet.balance < Decimal(adjusted_amount):
#             return Response({"error": "Insufficient wallet balance."}, status=400)

#         # ✅ Deduct from wallet
#         wallet.balance -= Decimal(adjusted_amount)
#         wallet.save()
#         print("✅ Deducted. New balance:", wallet.balance)

#         request_id = str(uuid.uuid4())

#         # ✅ ClubKonnect API call
#         clubkonnect_url = "https://www.nellobytesystems.com/APIAirtimeV1.asp"
#         params = {
#             "UserID": settings.CLUBKONNECT_USERID,
#             "APIKey": settings.CLUBKONNECT_APIKEY,
#             "MobileNetwork": network,
#             "Amount": str(amount),  # Send raw amount to ClubKonnect
#             "MobileNumber": phone,
#             "RequestID": request_id,
#             "CallBackURL": "https://yourdomain.com/webhook/"  # optional
#         }

#         try:
#             response = requests.get(clubkonnect_url, params=params, timeout=10)
#             result = response.json()

#             api_status = result.get("Status") or result.get("status")
#             if api_status and api_status.lower() in ["successful", "order_received"]:
#                 final_status = "success"
#             else:
#                 wallet.balance += Decimal(adjusted_amount)  # refund
#                 wallet.save()
#                 final_status = "failed"

#         except Exception as e:
#             wallet.balance += Decimal(adjusted_amount)  # refund
#             wallet.save()
#             return Response({"error": f"API request failed: {str(e)}"}, status=500)

#         # ✅ Save transaction
#         Transaction.objects.create(
#             user=user,
#             txn_type='airtime',
#             amount=Decimal(adjusted_amount),
#             status=final_status,
#             reference=request_id,
#             meta=result
#         )

#         return Response({
#             "message": "Airtime request sent.",
#             "status": final_status,
#             "api_response": result
#         }, status=200)
    
    







    # -----------------------DATA VIEW --------------------------------



class DataPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = request.data.get('phone')
        network = request.data.get('network')      # E.g., "01", "02", "03", "04"
        data_plan = request.data.get('data_plan')  # E.g., "1000.0"
        base_amount = request.data.get('amount')   # Sent from frontend

        user = request.user

        if not all([base_amount, phone, network, data_plan]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            real_amount = Decimal(str(base_amount))
        except Exception:
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        # Apply markup for non-staff users
        adjusted_amount = real_amount
        if not user.is_staff:
            if network == "01":       # MTN
                adjusted_amount += real_amount * Decimal("0.02") #2%
            elif network == "03":     # Airtel
                adjusted_amount += real_amount * Decimal("0.03") #3%
            elif network == "02":     # Glo
                adjusted_amount += real_amount * Decimal("0.035") #3.5%
            elif network == "04":     # 9mobile
                adjusted_amount += real_amount * Decimal("0.055") #5.5%

        adjusted_amount = adjusted_amount.quantize(Decimal("1."))  # Round to whole naira

        # Get wallet
        try:
            wallet = UserWallet.objects.get(user=user)
        except UserWallet.DoesNotExist:
            return Response({"error": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)

        if wallet.balance < adjusted_amount:
            return Response({"error": "Insufficient wallet balance."}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct wallet balance
        wallet.balance -= adjusted_amount
        wallet.save()

        # Generate unique transaction ID
        request_id = str(uuid.uuid4())[:10]

        # Call ClubKonnect
        url = (
            f"{settings.CLUBKONNECT_DATA_URL}"
            f"?UserID={settings.CLUBKONNECT_USERID}"
            f"&APIKey={settings.CLUBKONNECT_APIKEY}"
            f"&MobileNetwork={network}"
            f"&DataPlan={data_plan}"
            f"&MobileNumber={phone}"
            f"&RequestID={request_id}"
            f"&CallBackURL={settings.CLUBKONNECT_CALLBACK}"
        )

        try:
            response = requests.get(url)
            result = response.json()
        except Exception as e:
            # Refund wallet on failure
            wallet.balance += adjusted_amount
            wallet.save()
            return Response({"error": "Failed to contact data provider."}, status=status.HTTP_502_BAD_GATEWAY)

        # Log transaction
        Transaction.objects.create(
            user=user,
            txn_type='data',
            amount=adjusted_amount,
            status=result.get("orderstatus", "pending").lower(),
            reference=request_id,
            # meta=result
            meta={"raw_response": response.text}
        )

        return Response({
            "message": "✅ Data purchase initiated.",
            "order_status": result.get("status"),
            "real_amount": str(real_amount),
            "adjusted_amount": str(adjusted_amount),
            "phone": phone,
            "network": network,
            "data_plan": data_plan,
            "transaction_id": request_id,
            "api_response": result
        }, status=status.HTTP_200_OK)








from decimal import Decimal, ROUND_HALF_UP

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_data_plans(request):
    from decimal import Decimal, ROUND_HALF_UP

    network = request.GET.get("network")

    if not network:
        return JsonResponse({"error": "Network parameter is required."}, status=400)

    # ✅ Use exact ClubKonnect values: 'MTN', 'Glo', 'm_9mobile', 'Airtel'
    clubkonnect_values = ['MTN', 'Glo', 'm_9mobile', 'Airtel']

    # Match exact label, ignoring case
    matched_value = next((val for val in clubkonnect_values if val.lower() == network.lower()), None)

    if not matched_value:
        return JsonResponse({"error": f"Unsupported network: {network}"}, status=400)

    url = (
        f"{settings.CLUBKONNECT_DATA_PLAN_LIST_URL}"
        f"?UserID={settings.CLUBKONNECT_USERID}"
        f"&APIKey={settings.CLUBKONNECT_APIKEY}"
        f"&MobileNetwork={matched_value}"
    )

    try:
        print("📤 Request URL:", url)
        response = requests.get(url)
        data = response.json()

        print("📡 Available networks:", list(data.get("MOBILE_NETWORK", {}).keys()))
        print("🔍 Raw Response for Network:", matched_value)

        mobile_networks = data.get("MOBILE_NETWORK", {})
        network_data_list = mobile_networks.get(matched_value)

        if not network_data_list or not isinstance(network_data_list, list):
            return JsonResponse({"error": f"No data list found for {matched_value}", "raw": data}, status=502)

        products = network_data_list[0].get("PRODUCT", [])
        if not products:
            return JsonResponse({"error": f"No products found for {matched_value}", "raw": data}, status=502)

        output = []
        for item in products:
            output.append({
                "code": item.get("PRODUCT_ID"),
                "name": item.get("PRODUCT_NAME"),
                "price": int(Decimal(item.get("PRODUCT_AMOUNT", "0")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
            })

        return JsonResponse(output, safe=False)

    except Exception as e:
        return JsonResponse({"error": "Failed to fetch plans", "detail": str(e)}, status=500)




# ---------------------------CABLE VIEW -------------------------------


class CableTVPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = request.GET.get("provider")
        if not provider:
            return Response({"error": "Provider is required."}, status=status.HTTP_400_BAD_REQUEST)

        packages = CablePackage.objects.filter(provider=provider.lower())
        if not packages.exists():
            return Response({"error": "No packages found for this provider."}, status=status.HTTP_404_NOT_FOUND)

        data = [
            {"code": pkg.code, "name": pkg.name, "amount": int(pkg.amount)}
            for pkg in packages
        ]
        return Response(data, status=status.HTTP_200_OK)
    
    def post(self, request):
        smartcard = request.data.get("smartcard")
        phone = request.data.get("phone")
        cabletv = request.data.get("cabletv")  # e.g., dstv, gotv
        package = request.data.get("package")  # e.g., dstv-yanga
        amount = request.data.get("amount")    # must match the selected package

        if not all([smartcard, phone, cabletv, package, amount]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(amount)
        except:
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wallet = UserWallet.objects.get(user=request.user)
        except UserWallet.DoesNotExist:
            return Response({"error": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)

        if wallet.balance < amount:
            return Response({"error": "Insufficient wallet balance."}, status=status.HTTP_400_BAD_REQUEST)

        request_id = str(uuid.uuid4())
        callback_url = "https://192.168.0.199:8000/callback"

        api_url = (
            f"{settings.CLUBKONNECT_CABLE_URL}?UserID={settings.CLUBKONNECT_USERID}"
            f"&APIKey={settings.CLUBKONNECT_APIKEY}"
            f"&CableTV={cabletv}&Package={package}&SmartCardNo={smartcard}"
            f"&PhoneNo={phone}&RequestID={request_id}&CallBackURL={callback_url}"
        )

        try:
            response = requests.get(api_url)
            data = response.json()
            print("CLUBKONNECT SUBSCRIBE RESPONSE:", data) 
        except Exception as e:
            return Response({"error": "Failed to contact provider."}, status=status.HTTP_502_BAD_GATEWAY)

        if data.get("statuscode") == "100":
            wallet.balance -= amount
            wallet.save()

            Transaction.objects.create(
                user=request.user,
                txn_type='cable',
                amount=amount,
                status='success',
                reference=data.get("orderid", request_id),
                meta={
                    "package": package,
                    "smartcard": smartcard,
                    "phone": phone,
                    "provider": cabletv,
                    "response": response.text
                }
            )

            return Response({
                "message": "Cable TV subscription successful.",
                "order_id": data.get("orderid"),
                "status": data.get("status"),
                "amount": str(amount)
            })

        return Response({
            "error": "Subscription failed.",
            "details": data
        }, status=status.HTTP_400_BAD_REQUEST)









from django.http import JsonResponse
from .models import CablePackage

def cable_packages(request):
    provider = request.GET.get('provider')
    packages = CablePackage.objects.filter(provider=provider)

    data = [
        {"code": pkg.code, "name": pkg.name, "amount": pkg.amount}
        for pkg in packages
    ]
    return JsonResponse(data, safe=False)


from .models import SmartcardHistory

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verify_smartcard(request):
    provider = request.GET.get("provider")  # dstv, gotv, startimes
    smartcard = request.GET.get("smartcard")

    print("DEBUG‑USERID:", settings.CLUBKONNECT_USERID)
    print("DEBUG‑APIKEY:", settings.CLUBKONNECT_APIKEY)

    if not provider or not smartcard:
        return Response({"error": "Missing provider or smartcard"}, status=400)

    url = (
        f"{settings.CLUBKONNECT_VERIFY_URL}?"
        f"UserID={settings.CLUBKONNECT_USERID}"
        f"&APIKey={settings.CLUBKONNECT_APIKEY}"
        f"&CableTV={provider}&SmartCardNo={smartcard}"

        
    )
    print("Clubkonnect Verify URL:", url)

    try:
        res = requests.get(url, timeout=15)
        print("CLUBKONNECT RESPONSE:", res.text)  # 👈 Add this line

        data = res.json()
    except Exception:
        return Response({"error": "Unable to connect to Clubkonnect"}, status=502)

    if data.get("status") == "00":
        SmartcardHistory.objects.update_or_create(
        user=request.user,
        provider=provider,
        smartcard=smartcard,
        defaults={"customer_name": data.get("customer_name", "")}
        )
        return Response({
            "statuscode": "100",
            "name": data.get("customer_name"),
            "raw": data
        })
    else:
        return Response({
            "statuscode": "101",
            "error": data.get("status") or "Verification failed",
            "raw": data
        }, status=400)
        

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_saved_smartcards(request):
    provider = request.GET.get("provider")
    if not provider:
        return Response({"error": "Provider required"}, status=400)

    cards = SmartcardHistory.objects.filter(user=request.user, provider=provider).order_by("-last_used")[:3]
    data = [{"smartcard": c.smartcard, "name": c.customer_name} for c in cards]
    return Response(data)



    # -----------------------ELECTRICITY--------------------




# @csrf_exempt
# @login_required

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buy_electricity(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    user = request.user
    data = request.POST

    disco = data.get('disco')  # e.g., '01', '02', etc.
    meter_no = data.get('meter_no')
    meter_type = data.get('meter_type') # e.g. "01" for Prepaid, "02" for Postpaid
    phone = data.get('phone')
    amount_str = data.get('amount')

    # Validate required fields
    if not all([disco, meter_no, meter_type, phone, amount_str]):
        return JsonResponse({'error': 'All fields are required'}, status=400)

    try:
        amount = Decimal(amount_str)
    except:
        return JsonResponse({'error': 'Invalid amount format'}, status=400)

    try:
        wallet = UserWallet.objects.get(user=user)
        if wallet.balance < amount:
            return JsonResponse({'error': 'Insufficient wallet balance.'}, status=400)
    except UserWallet.DoesNotExist:
        return JsonResponse({'error': 'Wallet not found.'}, status=404)

    request_id = str(uuid.uuid4())

    # Build API payload (POST recommended by ClubKonnect)
    payload = {
        "UserID": settings.CLUBKONNECT_USERID,
        "APIKey": settings.CLUBKONNECT_APIKEY,
        "ElectricCompany": disco,
        "MeterType": meter_type,
        "MeterNo": meter_no,
        "Amount": str(amount),
        "PhoneNo": phone,
        "RequestID": request_id,
        "CallBackURL": settings.CLUBKONNECT_CALLBACK
    }

    try:
        response = requests.post(settings.CLUBKONNECT_ELECTRICITY_URL, data=payload, timeout=15)
        print("ClubKonnect Raw Response:", response.text)

        if not response.text:
            return JsonResponse({'error': 'Empty response from provider'}, status=502)

        res_data = response.json()

    except ValueError as e:
        # JSON decoding failed
        print("JSON decode error:", e, "Response was:", response.text)
        Transaction.objects.create(
            user=user,
            txn_type='electricity',
            amount=amount,
            status='failed',
            reference=request_id,
            meta={'error': 'Invalid JSON', 'response': response.text}
        )
        return JsonResponse({'error': 'Invalid response format from provider'}, status=502)

    except Exception as e:
        # Network or other error
        print("Connection error:", e)
        Transaction.objects.create(
            user=user,
            txn_type='electricity',
            amount=amount,
            status='failed',
            reference=request_id,
            meta={'error': str(e)}
        )
        return JsonResponse({'error': 'Electricity purchase failed', 'detail': str(e)}, status=502)

    # Handle success/failure based on ClubKonnect response
    status_code = str(res_data.get("status") or res_data.get("Status", "")).lower()
    message = res_data.get("message") or res_data.get("Message", "No message provided")

    # if status_code == "successful":
    if status_code in ["successful", "success"]:
    
        # Deduct from wallet
        wallet.balance -= amount
        wallet.save()

        # Record transaction
        Transaction.objects.create(
            user=user,
            txn_type='electricity',
            amount=amount,
            status='success',
            reference=request_id,
            meta=res_data
        )

        return JsonResponse({'message': 'Electricity purchase successful', 'data': res_data}, status=200)

    else:
        # Log failed transaction
        Transaction.objects.create(
            user=user,
            txn_type='electricity',
            amount=amount,
            status='failed',
            reference=request_id,
            meta=res_data
        )

        return JsonResponse({'error': 'Purchase failed', 'message': message, 'response': res_data}, status=400)





# views.py

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
import requests
import json

# @csrf_exempt
# @login_required

@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_meter_number(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    data = json.loads(request.body)
    meter_no = data.get("meter_no")
    disco = data.get("disco")

    if not meter_no or not disco:
        return JsonResponse({'error': 'Both meter_no and disco are required.'}, status=400)

    verify_url = (
    f"{settings.CLUBKONNECT_ELECTRICITY_VERIFY_URL}"
    f"?UserID={settings.CLUBKONNECT_USERID}"
    f"&APIKey={settings.CLUBKONNECT_APIKEY}"
    f"&ElectricCompany={disco}"
    f"&meterno={meter_no}"
)


    try:
        response = requests.get(verify_url, timeout=10)
        data = response.json()

        if "customer_name" in data and "INVALID" not in data["customer_name"]:
            return JsonResponse({'customer_name': data["customer_name"]})
        else:
            return JsonResponse({'error': 'Invalid meter number'}, status=400)

    except Exception as e:
        return JsonResponse({'error': 'Verification failed', 'detail': str(e)}, status=500)


# views.py
# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_electricity_providers(request):
    providers = [
        {"name": "Eko Electric - EKEDC", "code": "01"},
        {"name": "Ikeja Electric - IKEDC", "code": "02"},
        {"name": "Abuja Electric - AEDC", "code": "03"},
        {"name": "Kano Electric - KEDCO", "code": "04"},
        {"name": "Port Harcourt Electric - PHEDC", "code": "05"},
        {"name": "Jos Electric - JEDC", "code": "06"},
        {"name": "Ibadan Electric - IBEDC", "code": "07"},
        {"name": "Kaduna Electric - KAEDC", "code": "08"},
        {"name": "Enugu Electric - EEDC", "code": "09"},
        {"name": "Benin Electric - BEDC", "code": "10"},
        {"name": "Yola Electric - YEDC", "code": "11"},
        {"name": "Aba Electric - APLE", "code": "12"},
    ]
    return Response(providers)





# @csrf_exempt
# @login_required
# def buy_electricity(request):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Only POST method allowed'}, status=405)

#     user = request.user
#     # data = request.POST
#     data = json.loads(request.body)


#     disco = data.get('disco')  # e.g. "01"
#     meter_no = data.get('meter_no')
#     meter_type = data.get('meter_type')  # "01" or "02"
#     phone = data.get('phone')
#     # amount = Decimal(data.get('amount'))
#     try:
#         amount = Decimal(data.get('amount'))
#     except:
#         return JsonResponse({'error': 'Invalid amount'}, status=400)


#     if not all([disco, meter_no, meter_type, phone, amount]):
#         return JsonResponse({'error': 'All fields are required'}, status=400)

#     try:
#         wallet = UserWallet.objects.get(user=user)
#         if wallet.balance < amount:
#             return JsonResponse({'error': 'Insufficient wallet balance.'}, status=400)
#     except UserWallet.DoesNotExist:
#         return JsonResponse({'error': 'Wallet not found.'}, status=404)

#     request_id = str(uuid.uuid4())

#     url = (
#         f"{settings.CLUBKONNECT_ELECTRICITY_URL}?"
#         f"UserID={settings.CLUBKONNECT_USERID}&APIKey={settings.CLUBKONNECT_APIKEY}"
#         f"&ElectricCompany={disco}&MeterType={meter_type}&MeterNo={meter_no}"
#         f"&Amount={amount}&PhoneNo={phone}&RequestID={request_id}&CallBackURL={settings.CLUBKONNECT_CALLBACK}"
#     )

    

#     response = requests.get(url)
#     # res_data = response.json()
#     try:
#         res_data = response.json()
#     except ValueError:
#         return JsonResponse({
#         'error': 'Invalid response from provider',
#         'detail': response.text[:200]  # for debugging
#        }, status=502)


#     # Save ElectricityTransaction
#     elec_txn = ElectricityTransaction.objects.create(
#         user=user,
#         request_id=request_id,
#         order_id=res_data.get('orderid', ''),
#         disco=disco,
#         meter_no=meter_no,
#         meter_type=meter_type,
#         phone=phone,
#         amount=amount,
#         token=res_data.get('metertoken', ''),
#         status=res_data.get('status', 'FAILED')
#     )

#     # Debit wallet only if order was received
#     if res_data.get('statuscode') == "100":
#         wallet.balance -= amount
#         wallet.save()

#         # Save general Transaction
#         Transaction.objects.create(
#             user=user,
#             txn_type='electricity',
#             amount=amount,
#             status='success',
#             reference=request_id
#         )
#         return JsonResponse({
#             'success': True,
#             'message': 'Electricity purchase successful',
#             'order_id': res_data.get('orderid'),
#             'token': res_data.get('metertoken')
#         })

#     # Save failed transaction
#     Transaction.objects.create(
#         user=user,
#         txn_type='electricity',
#         amount=amount,
#         status='failed',
#         reference=request_id
#     )

#     return JsonResponse({'error': 'Electricity purchase failed', 'detail': res_data})




# # --------------WITHDRAWAL VIEW ------------------------

class WithdrawFundsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')
        bank_name = request.data.get('bank_name')
        account_number = request.data.get('account_number')
        account_name = request.data.get('account_name')

        if not all([amount, bank_name, account_number, account_name]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(amount)
        except:
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wallet = UserWallet.objects.get(user=request.user)
        except UserWallet.DoesNotExist:
            return Response({"error": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)

        if wallet.balance < amount:
            return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        # Simulate withdrawal by reducing wallet balance
        wallet.balance -= amount
        wallet.save()

        Transaction.objects.create(
            user=request.user,
            txn_type='withdraw',
            amount=amount,
            status='success',
            reference=str(uuid.uuid4())
        )

        return Response({
            "message": "Withdrawal successful (simulated).",
            "amount": str(amount),
            "bank_name": bank_name,
            "account_number": account_number,
            "account_name": account_name
        }, status=status.HTTP_200_OK)




# -------------------------TEST MODE AIRTIME-----------------------------

# class AirtimePurchaseView(APIView):
#     permission_classes = [IsAuthenticated]
#     TEST_MODE = True  # Toggle this to False when you're ready for live use

#     def post(self, request):
#         print("📥 Incoming POST:", request.data)

#         amount_raw = request.data.get('amount')
#         phone = request.data.get('phone')
#         network = request.data.get('network')  # Should be "01", "02", etc.
#         user = request.user

#         if not all([amount_raw, phone, network]):
#             return Response({"error": "All fields are required."}, status=400)

#         try:
#             amount = float(amount_raw)
#         except ValueError:
#             return Response({"error": "Invalid amount format."}, status=400)

#         # Apply markup if user is not admin
#         adjusted_amount = amount
#         if not user.is_staff:
#             if network == "01":       # MTN
#                 adjusted_amount *= 1.02
#             elif network == "04":     # 9mobile
#                 adjusted_amount *= 1.05
#             elif network == "02":     # Glo
#                 adjusted_amount *= 1.06
#             elif network == "03":     # Airtel
#                 adjusted_amount *= 1.02

#         adjusted_amount = round(adjusted_amount)

#         # Wallet deduction
#         try:
#             wallet = UserWallet.objects.get(user=user)
#         except UserWallet.DoesNotExist:
#             return Response({"error": "Wallet not found."}, status=404)

#         if wallet.balance < adjusted_amount:
#             return Response({"error": "Insufficient wallet balance."}, status=400)

#         wallet.balance -= Decimal(adjusted_amount)
#         wallet.save()

#         request_id = str(uuid.uuid4())

#         # Simulated or real API request
#         if self.TEST_MODE:
#             print("🧪 TEST MODE: Skipping real API call.")
#             result = {
#                 "status": "successful",
#                 "message": "Simulated airtime top-up",
#                 "simulated": True,
#                 "network": network,
#                 "phone": phone
#             }
#         else:
#             clubkonnect_url = "https://www.nellobytesystems.com/APIAirtimeV1.asp"
#             params = {
#                 "UserID": settings.CLUBKONNECT_USERID,
#                 "APIKey": settings.CLUBKONNECT_APIKEY,
#                 "MobileNetwork": network,
#                 "Amount": str(amount),  # original amount sent to API
#                 "MobileNumber": phone,
#                 "RequestID": request_id,
#                 "CallBackURL": settings.CLUBKONNECT_CALLBACK
#             }

#             try:
#                 response = requests.get(clubkonnect_url, params=params, timeout=10)
#                 result = response.json()
#             except Exception as e:
#                 wallet.balance += Decimal(adjusted_amount)
#                 wallet.save()
#                 return Response({"error": f"API request failed: {str(e)}"}, status=500)

#         # Record transaction
#         Transaction.objects.create(
#             user=user,
#             txn_type='airtime',
#             amount=Decimal(adjusted_amount),
#             status=result.get("status", "failed").lower(),
#             reference=request_id,
#             meta=result
#         )

#         return Response({
#             "message": "Airtime request processed.",
#             "test_mode": self.TEST_MODE,
#             "amount_deducted": str(adjusted_amount),
#             "original_amount": str(amount),
#             "network": network,
#             "api_response": result
#         }, status=200)



