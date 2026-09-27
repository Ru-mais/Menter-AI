import json
import base64
import hashlib
import requests

from vmentorai import settings

def encode_request(payload):
    """Base64 encode the payload"""
    return base64.b64encode(json.dumps(payload).encode()).decode()

def compute_x_verify(base64_payload, url_path):
    """Compute X-VERIFY header value"""
    data = f"{base64_payload}{url_path}{settings.PHONEPE_SALT_KEY}"
    checksum = hashlib.sha256(data.encode()).hexdigest()
    return f"{checksum}###{settings.PHONEPE_SALT_INDEX}"


def phonepe_post(url_path, payload):
    """Make a POST request to PhonePe API"""
    base64_payload = encode_request(payload)
    
    x_verify = compute_x_verify(base64_payload, url_path)
    
    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": x_verify,
    }
    
    request_data = {
        "request": base64_payload
    }
    
    response = requests.post(
        f"{settings.PHONEPE_BASE_URL}{url_path}",
        json=request_data,
        headers=headers,
        timeout=15
    )
    
    response.raise_for_status()
    
    return response.json()

def check_payment_status(merchant_txn_id):
    """Check payment status with PhonePe"""
    url_path = f"/pg/v1/status/{settings.PHONEPE_MERCHANT_ID}/{merchant_txn_id}"
    
    data = f"/pg/v1/status/{settings.PHONEPE_MERCHANT_ID}/{merchant_txn_id}{settings.PHONEPE_SALT_KEY}"
    checksum = hashlib.sha256(data.encode()).hexdigest()
    x_verify = f"{checksum}###{settings.PHONEPE_SALT_INDEX}"
    
    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": x_verify,
        "X-MERCHANT-ID": settings.PHONEPE_MERCHANT_ID
    }
    
    response = requests.get(
        f"{settings.PHONEPE_BASE_URL}{url_path}",
        headers=headers,
        timeout=15
    )
    
    response.raise_for_status()
    
    return response.json()