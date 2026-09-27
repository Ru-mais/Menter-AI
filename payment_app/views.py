import uuid
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from vmentorai import settings

from user_app.models import Userinfo, Payment
from .utils import phonepe_post, check_payment_status

PLAN_DETAILS = {
    "basic": {"amount": 49900, "label": "Basic – ₹499"},
    "pro": {"amount": 99900, "label": "Pro – ₹999"},
    "premium": {"amount": 149900, "label": "Premium – ₹1499"},
}

def payment(request):
    """Display payment plans page"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_app:login')
    
    try:
        user = Userinfo.objects.get(id=user_id)
        
        # user's current active plan
        current_plan = None
        current_payment = Payment.objects.filter(
            user=user, 
            status=Payment.COMPLETED
        ).order_by('-payment_date').first()
        
        if current_payment:
            current_plan = current_payment.plan
        
        context = {
            'first_name': user.first_name,
            'current_plan': current_plan,
            'plan_details': PLAN_DETAILS
        }
        
        return render(request, 'payment.html', context)
        
    except Userinfo.DoesNotExist:
        return redirect('user_app:login')

def subscribe(request, plan_key):
    """Initiate payment for selected plan"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_app:login')
    
    try:
        user = Userinfo.objects.get(id=user_id)
    except Userinfo.DoesNotExist:
        return redirect('user_app:login')
    
    plan = PLAN_DETAILS.get(plan_key)
    if not plan:
        messages.error(request, "Invalid plan selected")
        return redirect('payment_app:payment')
    
    merchant_txn_id = f"MTX{uuid.uuid4().hex[:12]}"
    
    payment = Payment.objects.create(
        user=user,
        plan=plan_key,
        amount=plan["amount"] / 100,  # convert from paise to rupees
        transaction_id=merchant_txn_id,
        status=Payment.PENDING
    )
    
    # payment payload
    payload = {
        "merchantId": settings.PHONEPE_MERCHANT_ID,
        "merchantTransactionId": merchant_txn_id,
        "merchantUserId": f"MUID_{user_id}",
        "amount": plan["amount"],
        "redirectUrl": request.build_absolute_uri(reverse('payment_app:confirm')) + f"?merchantTransactionId={merchant_txn_id}",
        "redirectMode": "REDIRECT",
        "callbackUrl": request.build_absolute_uri(reverse('payment_app:confirm')) + f"?merchantTransactionId={merchant_txn_id}",
        "mobileNumber": user.phone_number if hasattr(user, 'phone_number') and user.phone_number else "9999999999",
        "paymentInstrument": {
            "type": "PAY_PAGE"
        }
    }
    
    try:
        # initiate payment
        response = phonepe_post("/pg/v1/pay", payload)

        print("PhonePe Response:", response)
        
        if response.get("success"):
            data = response["data"]["instrumentResponse"]
            redirect_url = data.get("intentUrl") or data["redirectInfo"]["url"]
            return redirect(redirect_url)
        else:
            messages.error(request, f"Payment initiation failed: {response.get('message', 'Unknown error')}")
            payment.status = Payment.FAILED
            payment.save()
            return redirect('payment_app:error_page')
    
    except Exception as e:
        print(f"Error initiating payment: {str(e)}")
        messages.error(request, f"Error initiating payment: {str(e)}")
        payment.status = Payment.FAILED
        payment.save()
        return redirect('payment_app:error_page')

def confirm(request):
    """Handle redirect from PhonePe after payment"""
    merchant_txn_id = request.GET.get("merchantTransactionId")
    
    if not merchant_txn_id:
        messages.error(request, "Missing transaction information")
        return redirect('payment_app:error_page')
    
    payment = get_object_or_404(Payment, transaction_id=merchant_txn_id)
    
    try:
        # payment status
        status_response = check_payment_status(merchant_txn_id)
        
        if status_response.get("success"):
            status = status_response["data"]["state"]
            txn_id = status_response["data"].get("transactionId")
            
            if status == "COMPLETED":
                payment.status = Payment.COMPLETED
                payment.order_id = txn_id
                messages.success(request, "Payment successful! Your subscription is now active.")
            else:
                payment.status = Payment.FAILED
                messages.error(request, f"Payment failed with status: {status}")
            
            payment.save()
            
            if status == "COMPLETED":
                return redirect('payment_app:success')
            else:
                return redirect('payment_app:error_page')
        
        else:
            messages.error(request, f"Error checking payment status: {status_response.get('message', 'Unknown error')}")
            return redirect('payment_app:error_page')
    
    except Exception as e:
        print(f"Error checking payment status: {str(e)}")
        messages.error(request, f"Error processing payment confirmation: {str(e)}")
        return redirect('payment_app:error_page')

def success(request):
    """Display success page after payment"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_app:login')
    
    try:
        user = Userinfo.objects.get(id=user_id)
        payment = Payment.objects.filter(user=user, status=Payment.COMPLETED).order_by('-payment_date').first()
        
        context = {
            'user': user,
            'payment': payment,
            'payment_status': 'Success',
            'message': 'Your payment was successful!'
        }
        
        return render(request, 'success.html', context)
        
    except Userinfo.DoesNotExist:
        return redirect('user_app:login')

def error_page(request):
    """Display error page"""
    return render(request, 'error.html', {'message': 'There was an error processing your payment.'})
