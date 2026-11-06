# Firebase (Authentication and Cloud Messaging)

`app/services/firebase.py` provides `Firebase`, a wrapper around the
[Firebase Admin SDK](https://firebase.google.com/docs/admin/setup) for user management,
ID token verification, custom tokens and push notifications (FCM). Credentials are
modeled by `FirebaseServiceAccount` in `app/core/credentials/firebase.py`, the token
schemas live in `app/schemas/firebase.py`, and the exceptions in
`app/core/exceptions/firebase_exceptions.py`.

The integration is included when the project is generated with
`--data services=custom --data include_firebase=true` (or by answering "yes" to the
Firebase question). It adds `firebase-admin` to the project's dependencies and the
`FIREBASE_*` settings to `app/core/config.py`, `.env.example` and the backend service in
`docker-compose.yml`. Firestore is a separate choice under it, see
[firestore.md](firestore.md).

## Setup

1. **Create a Firebase project** in the [Firebase Console](https://console.firebase.google.com/).
2. **Create a service account key**: Project Settings → Service Accounts → Generate new private key.
3. **Fill in the settings** from the downloaded JSON (in `.env`, never in the repository):

   ```env
   FIREBASE_PROJECT_ID=
   FIREBASE_PRIVATE_KEY_ID=
   FIREBASE_PRIVATE_KEY=
   FIREBASE_CLIENT_EMAIL=
   FIREBASE_CLIENT_ID=
   ```

   Instead of putting the PEM key in `FIREBASE_PRIVATE_KEY`, you can set
   `FIREBASE_PRIVATE_KEY_PATH` to a file that holds it. `settings.firebase_credentials`
   assembles a `FirebaseServiceAccount` from these values.

## Usage

`Firebase()` initializes the Firebase app once per process (from
`settings.firebase_credentials`, or from a `FirebaseServiceAccount` you pass) and reuses
it afterwards. Every operation is `async`.

```python
from app.services.firebase import Firebase

firebase = Firebase()

# Users
user = await firebase.get_user_by_id("user_uid_123")
user = await firebase.get_user_by_email("user@example.com")
user = await firebase.get_user_by_phone_number("+1234567890")
users_page = await firebase.get_all_users(max_results=1000)
new_user = await firebase.create_user(email="new@example.com", display_name="New User")
await firebase.set_custom_claims(new_user.uid, {"role": "admin"})

# Tokens
custom_token = await firebase.create_custom_token(uid="user_uid_123", additional_claims={"premium": True})
decoded = await firebase.verify_id_token(id_token="token_from_the_client")  # DecodedFirebaseTokenResponse
print(decoded.uid, decoded.email)

# Push notifications (FCM)
if await firebase.validate_fcm_token("fcm_device_token"):
    await firebase.notify_a_device(device_token="fcm_device_token", title="Hello", content="Welcome!")
sent = await firebase.notify_multiple_devices(device_tokens=["token_1", "token_2"], title="News", content="...")
```

### In an endpoint

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.services.firebase import Firebase

router = APIRouter()


def get_firebase() -> Firebase:
    return Firebase()


@router.get("/firebase/me")
async def firebase_me(
    firebase: Annotated[Firebase, Depends(get_firebase)],
    authorization: Annotated[str, Header()],
):
    token = authorization.removeprefix("Bearer ").strip()
    try:
        decoded = await firebase.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token")
    return {"uid": decoded.uid, "email": decoded.email}
```

## Production

1. **Projects and keys**
   - Use a separate Firebase project per environment (dev, staging, production)
   - Restrict the service account to the permissions the app needs; rotate its keys
   - Keep the key out of the image and the repository (environment or mounted secret)
2. **Security**
   - Enable Firebase App Check for client-facing APIs
   - Monitor usage and quotas, and set budget alerts
3. **Push notifications**
   - Configure APNs for iOS and notification channels for Android
   - Refresh device tokens in the clients and remove expired tokens on the server
   - Watch delivery success rates; `notify_multiple_devices` sends in batches of up to 500
