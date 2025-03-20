import razorpay
from django.conf import settings


def create_razorpay_order(amount, currency="INR", receipt=None):
    """Creates a Razorpay order and returns the order details."""
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
    
    data = {
        "amount": int(amount * 100),  # Convert amount to paisa
        "currency": currency,
        "receipt": receipt,
        "payment_capture": 1,  # Auto-capture payment
    }

    try:
        order = client.order.create(data)
        return order  # Returns Razorpay order details
    except razorpay.errors.RazorpayError as e:
        return {"error": str(e)}
    

def verify_razorpay_signature(response_data):
        """Verifies Razorpay payment signature to confirm authenticity."""
        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

        # Extract required parameters
        payment_id = response_data.get("razorpay_payment_id")
        order_id = response_data.get("razorpay_order_id")
        signature = response_data.get("razorpay_signature")

        if not payment_id or not order_id or not signature:
            return False  # Missing required data
        
        try:
            client.utility.verify_payment_signature(response_data)
            return True  # Signature is valid
        except razorpay.errors.SignatureVerificationError:
            return False  # Signature is invalid