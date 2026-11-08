# Firestore

`app/services/firestore.py` provides `Firestore`, an async document-store client built on
the Firebase Admin SDK (`firebase_admin.firestore_async`). It uses the same service
account as [Firebase](firebase.md); its errors are `FirebaseFirestoreError` and
`FirebaseDocumentNotFoundError` in `app/core/exceptions/firebase_exceptions.py`.

Firestore can only be included together with Firebase: generate the project with
`--data services=custom --data include_firebase=true --data include_firestore=true` (the
Firestore question is asked only after "yes" to Firebase). It needs no extra dependency
beyond `firebase-admin`.

## Setup

Set the `FIREBASE_*` settings as described in [firebase.md](firebase.md), and create a
Firestore database in the same Firebase project (Firebase Console → Firestore Database).

## Usage

```python
from app.core.config import settings
from app.core.exceptions.firebase_exceptions import FirebaseDocumentNotFoundError
from app.services.firestore import Firestore

firestore = Firestore(settings.firebase_credentials)

await firestore.add_document("users", "user_123", {"name": "John Doe", "email": "john@example.com"})
user = await firestore.get_document("users", "user_123")  # dict | None
await firestore.update_document("users", "user_123", {"last_login": "2026-01-01T00:00:00Z"})
all_users = await firestore.fetch_all_documents("users")  # list[dict]
await firestore.remove_document("users", "user_123")

try:
    await firestore.update_document("users", "missing", {"x": 1})
except FirebaseDocumentNotFoundError as exc:
    print(f"Document not found: {exc}")
```

### In an endpoint

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.exceptions.firebase_exceptions import FirebaseDocumentNotFoundError
from app.services.firestore import Firestore

router = APIRouter()


def get_firestore() -> Firestore:
    return Firestore(settings.firebase_credentials)


@router.put("/preferences/{user_id}")
async def update_preferences(user_id: str, prefs: dict, firestore: Annotated[Firestore, Depends(get_firestore)]):
    try:
        await firestore.update_document("user_preferences", user_id, prefs)
    except FirebaseDocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return {"updated": True}
```

## When to use Firestore alongside PostgreSQL

Firestore suits user preferences and UI state, real-time data (chat, activity feeds),
session-like data without relational integrity, device tokens and analytics events.
Keep transactional and relational data (orders, payments, anything that needs foreign
keys, ACID transactions, JOINs or aggregations) in PostgreSQL.

## Production

- Write Firestore security rules; for example, users may only access their own
  documents and some collections are server-write only:

  ```javascript
  rules_version = '2';
  service cloud.firestore {
    match /databases/{database}/documents {
      match /user_preferences/{userId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
      match /analytics/{document=**} {
        allow read: if request.auth != null;
        allow write: if false; // server-side only
      }
    }
  }
  ```

- Add indexes for the queries you run, paginate large collections, and watch the
  read/write counts (they drive the cost)
