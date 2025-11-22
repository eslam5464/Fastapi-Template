import hashlib
import time
import uuid
from pathlib import Path

import aiohttp
from fastapi import Request

from app.core.config import Environment, settings


def parse_user_id(user_id: str | int | uuid.UUID) -> str | int | uuid.UUID:
    """
    Parse user_id to appropriate type

    Args:
        user_id (str | int | uuid.UUID): The user ID to parse

    Returns:
        user_id (str | int | uuid.UUID): Parsed user ID
    """
    if isinstance(user_id, uuid.UUID):
        return user_id

    try:
        return uuid.UUID(str(user_id))
    except ValueError:
        pass

    try:
        return int(user_id)
    except (ValueError, TypeError):
        pass

    return user_id


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request headers or remote address

    Args:
        request: FastAPI request object

    Returns:
        Client IP address as a string
    """
    if settings.current_environment == Environment.LOCAL:
        return "localhost"

    if "X-Forwarded-For" in request.headers:
        return request.headers["X-Forwarded-For"].split(",")[0].strip()

    if "X-Real-IP" in request.headers:
        return request.headers["X-Real-IP"].strip()

    if "X-Client-IP" in request.headers:
        return request.headers["X-Client-IP"].strip()

    return request.client.host if request.client else "unknown"


def calculate_md5_hash(file_location: str) -> str:
    """
    Calculates the MD5 hash of a file.
    :param file_location: The file path of the input file for which the MD5 hash is to be calculated.
    :return: The computed MD5 hash of the file as a hexadecimal string.
    :raises FileNotFoundError: If the specified file does not exist at the provided file location.
    """
    if not Path(file_location).exists():
        raise FileNotFoundError(f"File not found in {file_location}")

    hash_md5 = hashlib.md5()

    with open(file_location, "rb") as file_binary:
        for chunk in iter(lambda: file_binary.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


async def estimate_upload_time(
    url: str = "httpbin.org",
    path: str = "/post",
    port: int = 443,
    file_size_mb: int = 1,
) -> float:
    """
    Asynchronously estimates the upload time to a specified server endpoint.

    Args:
        url (str): The base URL of the server (without protocol) to which data will be uploaded.
        path (str): The specific path on the server for the upload endpoint.
        port (int): The port number to use for the connection (443 for HTTPS, 80 for HTTP).
        file_size_mb (int): The size of the file to be uploaded in megabytes.

    Returns:
        float: The estimated time in seconds to upload the file.

    Raises:
        aiohttp.ClientError: If there is an error during the HTTP request.
    """
    async with aiohttp.ClientSession() as session:
        # Determine protocol based on port
        if url.startswith(("http://", "https://")):
            full_url = f"{url}{path}"
        else:
            protocol = "https" if port == 443 else "http"
            # Only include port if it's non-standard
            if (protocol == "https" and port != 443) or (protocol == "http" and port != 80):
                full_url = f"{protocol}://{url}:{port}{path}"
            else:
                full_url = f"{protocol}://{url}{path}"

        sample_data = b"x" * (1024 * 1024)  # 1 MB of data
        headers = {
            "Content-Type": "application/octet-stream",
        }
        start_time = time.time()

        async with session.post(url=full_url, headers=headers, data=sample_data):
            end_time = time.time()

    elapsed_time = end_time - start_time
    upload_speed_MBps = len(sample_data) / (elapsed_time * 1024 * 1024)  # MB/s

    return file_size_mb / upload_speed_MBps
