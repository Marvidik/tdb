from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes
from django.contrib.auth import authenticate
from django.utils.timezone import localtime,now
from rest_framework.permissions import IsAuthenticated
from user.models import UserAccount, DomesticTransfer, InterBankTransfer, WireTransfer
from decimal import Decimal
from django.db import transaction

CustomUser = get_user_model()

@api_view(["POST"])
@permission_classes([AllowAny])
def create_account(request):
    data = request.data

    # Required fields
    required_fields = ["first_name", "last_name", "username", "password", "email"]
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return Response(
            {"status": "error", "message": f"Missing fields: {', '.join(missing_fields)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate email
    try:
        validate_email(data["email"])
    except ValidationError:
        return Response(
            {"status": "error", "message": "Invalid email address"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if username or email already exists
    if CustomUser.objects.filter(username=data["username"]).exists():
        return Response({"status": "error", "message": "Username already exists"}, status=400)
    if CustomUser.objects.filter(email=data["email"]).exists():
        return Response({"status": "error", "message": "Email already exists"}, status=400)

    # Create user
    user = CustomUser(
        first_name=data["first_name"],
        middle_name=data.get("middle_name"),
        last_name=data["last_name"],
        username=data["username"],
        email=data["email"],
        occupation=data.get("occupation"),
        phone_number=data.get("phone_number"),
        date_of_birth=data.get("date_of_birth"),
        marital_status=data.get("marital_status"),
        gender=data.get("gender"),
        address=data.get("address"),
        account_type=data.get("account_type", "savings"),
        account_currency=data.get("account_currency", "usd")
    )
    user.set_password(data["password"])
    user.save()

    # Generate token
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        "status": "success",
        "message": "Account created successfully",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "middle_name": user.middle_name,
            "last_name": user.last_name,
            "token": token.key
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_account(request):
    data = request.data
    username_or_email = data.get("username_or_email")
    password = data.get("password")

    if not username_or_email or not password:
        return Response(
            {"status": "error", "message": "username_or_email and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Allow login via username or email
    try:
        user = CustomUser.objects.get(email=username_or_email)
        username = user.username
    except CustomUser.DoesNotExist:
        username = username_or_email

    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {"status": "error", "message": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        "status": "success",
        "message": "Login successful",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "token": token.key
        }
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_statement(request):
    user = request.user

    # Get or create the user's account
    account, created = UserAccount.objects.get_or_create(
        user=user,
        defaults={"account_balance": 0}
    )

    # Collect transactions
    domestic = DomesticTransfer.objects.filter(user=user)
    interbank = InterBankTransfer.objects.filter(user=user)
    wire = WireTransfer.objects.filter(user=user)

    # Format transactions
    transactions = []

    for tx in domestic:
        transactions.append({
            "id": tx.id,
            "type": tx.transaction_type,
            "amount": float(tx.amount),
            "description": tx.description,
            "beneficiary_name": tx.beneficiary_name,
            "beneficiary_account": tx.beneficiary_account_number,
            "bank_name": tx.bank_name,
            "account_type": tx.account_type,
            "date": localtime(tx.date).strftime("%Y-%m-%d %H:%M:%S"),
            "status": tx.status
        })

    for tx in interbank:
        transactions.append({
            "id": tx.id,
            "type": tx.transaction_type,
            "amount": float(tx.amount),
            "description": tx.description,
            "beneficiary_name": tx.beneficiary_name,
            "iban": tx.iban,
            "bank_name": tx.bank_name,
            "account_type": tx.account_type,
            "country": tx.country,
            "date": localtime(tx.date).strftime("%Y-%m-%d %H:%M:%S"),
            "status": tx.status
        })

    for tx in wire:
        transactions.append({
            "id": tx.id,
            "type": tx.transaction_type,
            "amount": float(tx.amount),
            "description": tx.description,
            "beneficiary_name": tx.beneficiary_name,
            "routing_number": tx.routing_number,
            "iban": tx.iban,
            "bank_name": tx.bank_name,
            "swift_code": tx.swift_code,
            "country": tx.country,
            "account_type": tx.account_type,
            "date": localtime(tx.date).strftime("%Y-%m-%d %H:%M:%S"),
            "status": tx.status
        })

    # Sort transactions by date descending
    transactions.sort(key=lambda x: x["date"], reverse=True)

    return Response({
        "status": "success",
        "message": "Account balance and statement retrieved successfully",
        "data": {
            "account_number": account.account_number if hasattr(account, "account_number") else None,
            "account_balance": float(account.account_balance),
            "transactions": transactions
        }
    })



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def make_domestic_transfer(request):
    user = request.user
    data = request.data

    # ✅ Require password confirmation
    input_password = data.get("password")
    if not input_password:
        return Response({"status": "error", "message": "Password required"}, status=400)

    user_auth = authenticate(username=user.username, password=input_password)
    if user_auth is None:
        return Response({"status": "error", "message": "Invalid password"}, status=403)

    # ✅ Ensure user has an account
    account, _ = UserAccount.objects.get_or_create(user=user, defaults={"account_balance": 0})

    # ✅ Required fields
    required_fields = ["beneficiary_name", "beneficiary_account_number", "bank_name", "amount"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return Response({"status": "error", "message": f"Missing fields: {', '.join(missing)}"}, status=400)

    amount = Decimal(data["amount"])
    if amount <= 0:
        return Response({"status": "error", "message": "Amount must be > 0"}, status=400)

    if account.account_balance < amount:
        return Response({"status": "error", "message": "Insufficient funds"}, status=400)

    # ✅ Ensure receiver exists inside platform
    try:
        receiver_account = UserAccount.objects.get(account_number=data["beneficiary_account_number"])
    except UserAccount.DoesNotExist:
        return Response(
            {"status": "error", "message": "Beneficiary account does not exist in our system"},
            status=404
        )

    with transaction.atomic():
        # ✅ Deduct sender balance
        account.account_balance -= amount
        account.save()

        # ✅ Credit receiver balance
        receiver_account.account_balance += amount
        receiver_account.save()

        # ✅ Record transfer
        transfer = DomesticTransfer.objects.create(
            user=user,
            account=account,
            amount=amount,
            description=data.get("description", ""),
            status="completed",
            date=now(),
            beneficiary_name=data["beneficiary_name"],
            beneficiary_account_number=data["beneficiary_account_number"],
            bank_name=data["bank_name"],
            account_type=data.get("account_type", "savings"),
        )

    return Response({
        "status": "success",
        "message": "Domestic transfer completed successfully",
        "data": {
            "transfer_id": transfer.id,
            "amount": float(amount),
            "beneficiary_account": receiver_account.account_number,
            "account_balance": float(account.account_balance),
        }
    }, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def make_interbank_transfer(request):
    user = request.user
    data = request.data

    # Ensure the user has an account
    account, created = UserAccount.objects.get_or_create(
        user=user, defaults={"account_balance": 0}
    )

    # Required fields
    required_fields = [
        "beneficiary_name",
        "iban",
        "bank_name",
        "country",
        "amount",
        "password"
    ]
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return Response(
            {"status": "error", "message": f"Missing fields: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Confirm password
    password = data.get("password")
    if not user.check_password(password):
        return Response(
            {"status": "error", "message": "Invalid password"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Validate amount
    try:
        amount = Decimal(data["amount"])
    except:
        return Response(
            {"status": "error", "message": "Invalid amount format"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if amount <= 0:
        return Response(
            {"status": "error", "message": "Amount must be greater than 0"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check balance
    if account.account_balance < amount:
        return Response(
            {"status": "error", "message": "Insufficient funds"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Deduct balance
    account.account_balance -= amount
    account.save()

    # Create inter-bank transfer record
    transfer = InterBankTransfer.objects.create(
        user=user,
        account=account,
        amount=amount,
        description=data.get("description", ""),
        status="completed",  # or "pending"
        date=now(),
        beneficiary_name=data["beneficiary_name"],
        iban=data["iban"],
        bank_name=data["bank_name"],
        country=data["country"],
        account_type=data.get("account_type", "savings"),
    )

    return Response({
        "status": "success",
        "message": "Inter-bank transfer completed successfully",
        "data": {
            "transfer_id": transfer.id,
            "beneficiary_name": transfer.beneficiary_name,
            "iban": transfer.iban,
            "amount": float(transfer.amount),
            "bank_name": transfer.bank_name,
            "country": transfer.country,
            "date": transfer.date.strftime("%Y-%m-%d %H:%M:%S"),
            "account_balance": float(account.account_balance),
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def make_wire_transfer(request):
    user = request.user
    data = request.data

    required_fields = [
        "beneficiary_name", "routing_number", "iban", "bank_name",
        "swift_code", "country", "amount", "password"
    ]
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return Response(
            {"status": "error", "message": f"Missing fields: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check password
    if not user.check_password(data["password"]):
        return Response(
            {"status": "error", "message": "Invalid password"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Ensure account exists
    account, _ = UserAccount.objects.get_or_create(user=user, defaults={"account_balance": 0})

    amount = Decimal(data["amount"])
    if amount <= 0:
        return Response(
            {"status": "error", "message": "Amount must be greater than 0"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check balance
    if account.account_balance < amount:
        return Response(
            {"status": "error", "message": "Insufficient funds"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Deduct balance
    account.account_balance -= amount
    account.save()

    # Create wire transfer
    transfer = WireTransfer.objects.create(
        user=user,
        account=account,
        amount=amount,
        description=data.get("description", ""),
        status="completed",
        date=now(),
        beneficiary_name=data["beneficiary_name"],
        routing_number=data["routing_number"],
        iban=data["iban"],
        bank_name=data["bank_name"],
        swift_code=data["swift_code"],
        country=data["country"],
        account_type=data.get("account_type", "savings"),
    )

    return Response({
        "status": "success",
        "message": "Wire transfer completed successfully",
        "data": {
            "transfer_id": transfer.id,
            "beneficiary_name": transfer.beneficiary_name,
            "amount": float(transfer.amount),
            "bank_name": transfer.bank_name,
            "swift_code": transfer.swift_code,
            "date": transfer.date.strftime("%Y-%m-%d %H:%M:%S"),
            "account_balance": float(account.account_balance),
        }
    }, status=status.HTTP_201_CREATED)