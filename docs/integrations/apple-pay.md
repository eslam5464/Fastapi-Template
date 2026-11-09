# Apple Pay (App Store Server API)

`app/services/payments/apple_pay.py` wraps Apple's
[App Store Server Library](https://github.com/apple/app-store-server-library-python) to
verify in-app purchases and subscriptions. Credentials are modeled by
`ApplePayStoreCredentials` in `app/core/credentials/apple_pay.py` (built from settings by
`settings.apple_pay_store_credentials`), and errors are the `AppStore*Exception` classes
in `app/core/exceptions/apple_pay.py`.

The integration is included when the project is generated with
`--data services=custom --data include_apple_pay=true` (or by answering "yes" to the
Apple Pay question). It adds `app-store-server-library` to the dependencies and the
`APPLE_PAY_STORE_*` settings to `app/core/config.py`, `.env.example` and the backend
service in `docker-compose.yml`.

## Setup

1. **Create an App Store Connect API key**: App Store Connect → Users and Access →
   Integrations → In-App Purchase. Download the private key (`.p8`; it can only be
   downloaded once) and note the key ID and issuer ID.
2. **Download Apple's root certificate** `AppleRootCA-G3.cer` from
   [Apple PKI](https://www.apple.com/certificateauthority/).
3. **Configure `.env`**:

   ```env
   APPLE_PAY_STORE_PRIVATE_KEY_ID=YOUR_KEY_ID
   APPLE_PAY_STORE_PRIVATE_KEY_PATH=/run/secrets/SubscriptionKey.p8   # or the key itself in APPLE_PAY_STORE_PRIVATE_KEY
   APPLE_PAY_STORE_ISSUER_ID=YOUR_ISSUER_ID
   APPLE_PAY_STORE_BUNDLE_ID=com.yourcompany.yourapp
   APPLE_PAY_STORE_ROOT_CERTIFICATE_PATH=/run/secrets/AppleRootCA-G3.cer
   ```

The module builds a ready client at import time (`apple_pay` at the bottom of
`apple_pay.py`) from these settings. It talks to Apple's **sandbox** in the `LOCAL`,
`DEV` and `STG` environments and to production otherwise.

## Usage

Every call to Apple is `async`.

```python
from app.core.exceptions.apple_pay import AppStoreNotFoundException, AppStoreValidationException
from app.services.payments.apple_pay import apple_pay

transaction = await apple_pay.verify_transaction(transaction_id)
history = await apple_pay.get_transaction_history(original_transaction_id)
latest = apple_pay.get_latest_transaction(history)
statuses = await apple_pay.get_subscription_status(original_transaction_id)
refunds = await apple_pay.get_refund_history(original_transaction_id)

# Verify a purchase end to end and check it is the product you expect
transaction, decoded = await apple_pay.verify_and_process_subscription(
    transaction_id, expected_product_id="com.yourcompany.yourapp.premium"
)

# App Store Server Notifications (webhooks) and signed client payloads
notification = await apple_pay.verify_webhook_signature(signed_payload)
decoded_transaction = await apple_pay.decode_transaction_info(signed_transaction_info)
```

<!-- --- FEATURE[redis_cache] START --- -->
With the Redis cache, `get_subscription_status_cached(user_id, original_transaction_id,
force_refresh=False)` caches a user's subscription status for 10 minutes, and
`invalidate_subscription_cache(user_id)` drops it (call it from your webhook handler).

<!-- --- FEATURE[redis_cache] END --- -->
Failures raise `AppStoreNotFoundException`, `AppStoreValidationException`,
`AppStoreRateLimitExceededException`, `AppStoreInvalidCredentialsException` and the other
`AppStore*Exception` subclasses of `AppStoreException`.

### In an endpoint

```python
from fastapi import APIRouter, HTTPException

from app.core.exceptions.apple_pay import AppStoreNotFoundException, AppStoreValidationException
from app.services.payments.apple_pay import apple_pay

router = APIRouter()


@router.post("/purchases/{transaction_id}/verify")
async def verify_purchase(transaction_id: str):
    try:
        _, decoded = await apple_pay.verify_and_process_subscription(transaction_id)
    except AppStoreNotFoundException:
        raise HTTPException(status_code=404, detail="Transaction not found")
    except AppStoreValidationException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"product_id": decoded.productId, "expires": decoded.expiresDate}
```

## Use cases

- Verifying one-time purchases and subscriptions from iOS apps
- Checking subscription status and renewal information
- Retrieving a user's purchase history and detecting refunds
- Handling App Store Server Notifications (webhooks)
- Extending a subscription's renewal date (`extend_subscription_renewal_date`)

## Production

- Never commit the `.p8` key or put it in the image; inject it as a secret
- Use separate keys per environment and rotate them periodically
- Verify every purchase on the server; never trust a client's claim of a purchase
- Monitor for failed or unusual verification attempts
