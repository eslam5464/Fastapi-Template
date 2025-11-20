import base64
from datetime import datetime

from pydantic import HttpUrl, field_validator

from .base import BaseSchema


class ServiceAccount(BaseSchema):
    private_key: str
    private_key_id: str
    project_id: str
    client_email: str
    client_id: str


class BucketFile(BaseSchema):
    id: str
    basename: str
    extension: str
    file_path_in_bucket: str
    bucket_name: str
    authenticated_url: HttpUrl
    public_url: HttpUrl
    size_bytes: int
    md5_hash: str | None
    crc32c_checksum: int | None
    content_type: str | None
    metadata: dict | None = None
    creation_date: datetime
    modification_date: datetime

    @field_validator("md5_hash")
    def decode_md5_hash(cls, value: str) -> str:
        decoded_bytes = base64.b64decode(value)

        return decoded_bytes.hex()

    @field_validator("crc32c_checksum", mode="before")
    def decode_crc32c_checksum(cls, value: str) -> int:
        decoded_bytes = base64.b64decode(value)

        return int.from_bytes(decoded_bytes, byteorder="big")


class BucketFolder(BaseSchema):
    name: str
    bucket_folder_path: str
