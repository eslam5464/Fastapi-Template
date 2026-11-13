# Google Cloud Storage (GCS)

`app/services/gcs.py` provides `GCS`, an async client built on
[gcloud-aio-storage](https://github.com/talkiq/gcloud-aio) (file reads and writes use
`aiofiles`). Its exceptions live in `app/services/exceptions/gcs.py` and its
schemas (`ServiceAccount`, `BucketFile`, `BucketFolder`) in `app/schemas/google_bucket.py`.

The integration is included when the project is generated with
`--data services=custom --data include_gcs=true` (or by answering "yes" to the Google
Cloud Storage question). It adds `gcloud-aio-storage` and `aiofiles` to the project's
dependencies.

## Setup

1. **Create a service account** (Google Cloud Console → IAM & Admin → Service Accounts)
   with only the storage role the app needs (for example Storage Object Admin on one
   bucket), and create a JSON key for it.
2. **Pass the credentials at runtime.** `GCS` takes either a `ServiceAccount` (built
   from your own settings) or the path to the JSON key file. The template does not define
   GCS settings; add your own to `app/core/config.py` and `.env.example` if you want them
   configured through the environment, for example:

   ```env
   GCS_BUCKET_NAME=your-bucket-name
   GCS_CREDENTIALS_PATH=/run/secrets/gcs-service-account.json
   ```

## Usage

`GCS` is an async context manager: the storage session opens on enter and closes on
exit. Every method is `async`; `list_files` and `list_folders` are async generators.

```python
from io import BytesIO

from app.services.gcs import GCS

async with GCS("/path/to/service-account.json") as gcs:
    # Upload from disk or from memory; both return a BucketFile (or None)
    uploaded = await gcs.upload_file(
        bucket_name="my-bucket",
        file_path="/path/to/report.pdf",
        bucket_folder_path="documents",
    )
    await gcs.upload_bytesio(
        bucket_name="my-bucket",
        bytes_io=BytesIO(b"hello"),
        target_filename="hello.txt",
        bucket_folder_path="notes",
        content_type="text/plain",
    )

    # Look up files and folders
    file = await gcs.get_file("my-bucket", "documents/report.pdf")  # BucketFile | None
    async for item in gcs.list_files("my-bucket", folder_path_in_bucket="documents"):
        print(item.file_path_in_bucket, item.size_bytes, item.public_url)
    async for folder in gcs.list_folders("my-bucket"):
        print(folder.bucket_folder_path)

    # Download
    await gcs.download_file("my-bucket", "documents/report.pdf", destination_path="/tmp/report.pdf")
    data = await gcs.download_file_bytes("my-bucket", "documents/report.pdf")  # BytesIO | None

    # Organise and clean up
    await gcs.create_folder("my-bucket", "archive")
    await gcs.copy_file("my-bucket", "documents/report.pdf", "archive/report.pdf")
    await gcs.move_file("my-bucket", "notes/hello.txt", "archive/hello.txt")
    await gcs.delete_files("my-bucket", ["archive/report.pdf", "archive/hello.txt"])
```

`BucketFile` carries the object's `id`, `basename`, `extension`, `file_path_in_bucket`,
`authenticated_url`, `public_url`, `size_bytes`, decoded `md5_hash` (hex) and
`crc32c_checksum` (int), `content_type`, `metadata` and creation/modification dates.

Errors raise `GCSError` (or `GCSBucketNotFoundError` / `GCSBucketNotSelectedError`) from
`app.services.exceptions.gcs`; using the client outside `async with` raises
`GCSError`.

### In an endpoint

```python
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.services.gcs import GCS

router = APIRouter()


@router.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmp:
        temp_path = Path(tmp) / Path(file.filename or "upload").name
        temp_path.write_bytes(await file.read())

        # gcs_* are settings you add yourself (see Setup).
        async with GCS(settings.gcs_credentials_path) as gcs:
            uploaded = await gcs.upload_file(
                bucket_name=settings.gcs_bucket_name,
                file_path=str(temp_path),
                bucket_folder_path="uploads",
                content_type=file.content_type,
            )

    if uploaded is None:
        return {"uploaded": False}
    return {"uploaded": True, "path": uploaded.file_path_in_bucket, "url": str(uploaded.authenticated_url)}
```

## Production

- Use a separate service account per environment, with the least privilege that works
- Keep the JSON key out of the image and the repository (mount it as a secret)
- Enable uniform bucket-level access
- Configure lifecycle rules for automatic cleanup, and versioning for critical data
- Turn on Cloud Audit Logs for the bucket
