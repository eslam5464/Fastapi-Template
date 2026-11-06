# BackBlaze B2 Cloud Storage

`app/services/back_blaze_b2.py` wraps the [b2sdk](https://github.com/Backblaze/b2-sdk-python)
client for bucket management and file operations. Its exceptions live in
`app/core/exceptions/back_blaze_exceptions.py` and its schemas (`ApplicationData`,
`FileDownloadLink`, `UploadedFileInfo`) in `app/schemas/back_blaze_bucket.py`.

The integration is included when the project is generated with
`--data services=custom --data include_backblaze=true` (or by answering "yes" to the
BackBlaze question). It adds `b2sdk` to the project's dependencies.

## Setup

1. **Create a BackBlaze account** at [backblaze.com](https://www.backblaze.com/b2/cloud-storage.html).
2. **Create an application key** (App Keys page) with only the capabilities the app needs.
3. **Pass the credentials at runtime.** The service takes an `ApplicationData`
   (`app_id` = the key ID, `app_key` = the application key). The template does not
   define B2 settings; add your own to `app/core/config.py` and `.env.example` if you
   want them configured through the environment, for example:

   ```env
   B2_APPLICATION_KEY_ID=your_key_id_here
   B2_APPLICATION_KEY=your_application_key_here
   B2_BUCKET_NAME=your_bucket_name
   ```

## Usage

Every operation is `async` (the blocking b2sdk calls run in a worker thread), and the
client authorizes itself on first use.

```python
from pydantic import AnyUrl

from app.schemas import ApplicationData, UploadedFileInfo
from app.services.back_blaze_b2 import B2BucketTypeEnum, BackBlaze

b2_client = BackBlaze(ApplicationData(app_id="your_key_id", app_key="your_application_key"))

# Buckets
buckets = await b2_client.list_buckets()
await b2_client.create_bucket("my-new-bucket", B2BucketTypeEnum.ALL_PRIVATE)
await b2_client.select_bucket("my-bucket-name")

# Upload a file to the selected bucket
file_version = await b2_client.upload_file(
    local_file_path="/path/to/local/file.pdf",
    b2_file_name="documents/file.pdf",
    file_info=UploadedFileInfo(scanned=True),
)

# Download links
download_link = await b2_client.get_download_url_by_name("documents/file.pdf")
temp_link = await b2_client.get_temporary_download_link(
    url=AnyUrl(download_link.download_url),
    valid_duration_in_seconds=3600,  # 1 hour
)

# Delete the file, change or delete the bucket
await b2_client.delete_file(file_id=file_version.id_, file_name="documents/file.pdf")
await b2_client.update_selected_bucket(bucket_type=B2BucketTypeEnum.ALL_PUBLIC)
await b2_client.delete_selected_bucket()
```

### Features

- **Bucket management**: create, delete, update, list and select buckets
- **File operations**: upload, look up and delete files
- **Download URLs**: by file name, by file ID, and temporary authorized links for private buckets
- **Method chaining**: `select_bucket`, `create_bucket` and the update/delete methods return the client
- **Metadata**: custom file information with `UploadedFileInfo`
- **Errors**: failures raise a subclass of `BlackBlazeError` (`B2AuthorizationError`,
  `B2BucketNotFoundError`, `B2BucketNotSelectedError`, `B2BucketOperationError`,
  `B2FileOperationError`) from `app.core.exceptions.back_blaze_exceptions`, with the cause logged

### Bucket types

- `ALL_PUBLIC`: files are publicly readable
- `ALL_PRIVATE`: files need authorization
- `SNAPSHOT`: snapshot storage
- `SHARE`: shared access
- `RESTRICTED`: restricted access with authorization rules

### In an endpoint

```python
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import settings
from app.schemas import ApplicationData
from app.services.back_blaze_b2 import BackBlaze

router = APIRouter()


async def get_b2_client() -> BackBlaze:
    """Dependency returning a client with the upload bucket selected."""
    # b2_* are settings you add yourself (see Setup).
    client = BackBlaze(ApplicationData(app_id=settings.b2_app_id, app_key=settings.b2_app_key))
    return await client.select_bucket(settings.b2_bucket_name)


@router.post("/upload-document")
async def upload_document(
    b2_client: Annotated[BackBlaze, Depends(get_b2_client)],
    file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory() as tmp:
        temp_path = Path(tmp) / Path(file.filename or "upload").name
        temp_path.write_bytes(await file.read())

        result = await b2_client.upload_file(
            local_file_path=str(temp_path),
            b2_file_name=f"uploads/{temp_path.name}",
        )

    download_link = await b2_client.get_download_url_by_file_id(result.id_)
    return {"file_id": result.id_, "file_name": result.file_name, "download_url": download_link.download_url}
```

## Production

1. **Application keys**
   - Use separate keys per environment
   - Limit each key's capabilities and buckets to what the app needs
   - Rotate keys periodically
2. **Buckets**
   - Prefer `allPrivate` for sensitive data and hand out temporary links
   - Configure lifecycle rules if old file versions should expire
   - Set up CORS rules if browsers access the bucket directly
3. **Operations**
   - Monitor bucket access logs
   - Scan uploaded content before trusting it
   - Pick a region close to your users; use a CDN for public files
   - Enforce file size limits; use multipart uploads for large files
