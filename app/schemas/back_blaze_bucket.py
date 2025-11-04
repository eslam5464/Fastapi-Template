from .base import BaseSchema


class ApplicationData(BaseSchema):
    app_id: str
    app_key: str


class FileDownloadLink(BaseSchema):
    download_url: str
    auth_token: str | None = None


class UploadedFileInfo(BaseSchema):
    scanned: bool
