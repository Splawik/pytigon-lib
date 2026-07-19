import ipaddress
import os
import logging
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)

_SAFE_URL_PREFIXES = frozenset({"https", "http"})

# Cloud-provider metadata endpoints that must never be reachable via SSRF.
_METADATA_HOSTS = frozenset(
    {
        "localhost",  # resolves to loopback
        "metadata.google.internal",  # GCP
        "169.254.169.254",  # AWS / Azure / GCP link-local metadata
        "metadata.azure.com",  # Azure
        "169.254.169.253",  # Azure IMDS (alt)
        "100.100.100.200",  # Alibaba Cloud
    }
)


def _is_private_or_loopback_ip(ip_str: str) -> bool:
    """Return True if *ip_str* is a private, loopback, link-local, or
    multicast IP address (IPv4 or IPv6).

    Handles IP addresses in decimal, octal, hexadecimal, and integer
    notation by delegating to :func:`ipaddress.ip_address`, which rejects
    ambiguous forms only when strict=True; here we accept any form that
    Python's parser recognizes as a valid address.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _is_safe_url(url: str) -> bool:
    """Validate that *url* uses an allowed scheme and does not target
    internal, loopback, link-local, or cloud-metadata hosts (SSRF
    prevention).

    Note: this performs a static check on the hostname literal. DNS
    rebinding — where a hostname resolves to a public IP at check time
    but to a private IP at request time — is a known limitation; callers
    that need stronger guarantees should resolve the hostname and pin
    the IP for the actual request.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _SAFE_URL_PREFIXES:
        return False
    hostname = (parsed.hostname or "").lower().strip("[]")
    if not hostname:
        return False
    if hostname in _METADATA_HOSTS:
        return False
    # If the hostname is a literal IP, validate it directly. This catches
    # decimal/octal/hex/integer forms that the string-prefix checks below
    # would miss.
    if _is_private_or_loopback_ip(hostname):
        return False
    # Fallback string-prefix checks for hostnames that embed IPv4 ranges
    # (e.g. "10.evil.com" should not match the 10.0.0.0/8 rule, but
    # "10.0.0.5.evil.com" should be allowed — only literal IPs match).
    if hostname.startswith("169.254.") or hostname.startswith("10."):
        return False
    if hostname.startswith("172."):
        parts = hostname.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return False
    if hostname.startswith("192.168."):
        return False
    if hostname in ("0.0.0.0", "255.255.255.255"):
        return False
    return True


def _is_safe_tar_member(member: tarfile.TarInfo, target_path: str) -> bool:
    """Prevent path traversal in tar extraction."""
    resolved = os.path.realpath(os.path.join(target_path, member.name))
    target_real = os.path.realpath(target_path)
    return os.path.commonpath([resolved, target_real]) == target_real


def _is_safe_zip_member(member_name: str, target_path: str) -> bool:
    """Prevent path traversal in zip extraction."""
    resolved = os.path.realpath(os.path.join(target_path, member_name))
    target_real = os.path.realpath(target_path)
    return os.path.commonpath([resolved, target_real]) == target_real


def _safe_zip_extractall(zip_ref: zipfile.ZipFile, target_path: str) -> None:
    """Extract a zip file with path traversal protection."""
    for member in zip_ref.infolist():
        if member.filename.endswith(("/", "\\")):
            os.makedirs(os.path.join(target_path, member.filename), exist_ok=True)
        else:
            if _is_safe_zip_member(member.filename, target_path):
                zip_ref.extract(member, target_path)
            else:
                _logger.warning("Skipping unsafe zip entry: %s", member.filename)


def _safe_tar_extractall(tar_ref: tarfile.TarFile, target_path: str) -> None:
    """Extract a tar file with path traversal protection."""
    for member in tar_ref.getmembers():
        if member.isdir():
            os.makedirs(os.path.join(target_path, member.name), exist_ok=True)
        elif _is_safe_tar_member(member, target_path):
            tar_ref.extract(member, target_path)
        else:
            _logger.warning("Skipping unsafe tar entry: %s", member.name)


def download_and_process_file(file_list):
    """Detects the current OS, finds the matching item from the list,

    downloads the file (handling large files), and optionally unpacks it.
    """
    # 1. Detect the current operating system
    current_os = platform.system()
    _logger.info("Detected Operating System: %s", current_os)

    # 2. Find the matching row in the provided list
    matched_item = None
    for item in file_list:
        if item.get("os", "").strip().lower() == current_os.lower():
            matched_item = item
            break

    if not matched_item:
        _logger.error(
            "No configuration found for the current OS (%s) in the provided list.",
            current_os,
        )
        return

    # 3. Extract configuration data
    url = matched_item.get("url")
    target_path = matched_item.get("path")
    should_unpack = matched_item.get("unpack", False)

    if not _is_safe_url(url):
        _logger.error("URL is not allowed for security reasons: %s", url)
        return

    # Determine final file name for download
    # If unpacking, we extract the filename from URL to save it in temp first
    url_filename = url.split("/")[-1] if "/" in url else "downloaded_file"

    if should_unpack:
        # Create a secure temporary directory that is automatically cleaned up
        temp_dir = tempfile.mkdtemp()
        download_destination = os.path.join(temp_dir, url_filename[:64])
        _logger.info("Matching configuration found (Archive Mode)!")
        _logger.info(" -> URL: %s", url)
        _logger.info(" -> Temporary Download Path: %s", download_destination)
        _logger.info(" -> Final Extraction Directory: %s", target_path)
    else:
        download_destination = target_path
        _logger.info("Matching configuration found (Direct Download Mode)!")
        _logger.info(" -> URL: %s", url)
        _logger.info(" -> Target Path: %s", download_destination)

    # 4. Create required directories
    folder_to_create = target_path if should_unpack else os.path.dirname(target_path)
    if folder_to_create:
        os.makedirs(folder_to_create, exist_ok=True)

    # 5. Stream download with a progress bar
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        request = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(request) as response:
            total_size = response.headers.get("Content-Length")
            if total_size is not None:
                total_size = int(total_size)
            else:
                total_size = 0

            downloaded_bytes = 0
            block_size = 1024 * 1024  # 1 MB

            with open(download_destination, "wb") as local_file:
                while True:
                    block = response.read(block_size)
                    if not block:
                        break

                    local_file.write(block)
                    downloaded_bytes += len(block)

                    if total_size > 0:
                        percent = (downloaded_bytes / total_size) * 100
                        bar_length = 30
                        filled_length = int(bar_length * downloaded_bytes // total_size)
                        bar = "=" * filled_length + "." * (bar_length - filled_length)

                        mb_downloaded = downloaded_bytes / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)

                        sys.stdout.write(
                            f"\r   Downloading: [{bar}] {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)"
                        )
                    else:
                        mb_downloaded = downloaded_bytes / (1024 * 1024)
                        sys.stdout.write(
                            f"\r   Downloading: {mb_downloaded:.1f} MB downloaded (unknown total size)"
                        )

                    sys.stdout.flush()

            sys.stdout.write("\n   Status: Download successful!\n")

        # 6. Unpack logic (executed only if unpack is True)
            if should_unpack:
                _logger.info(" -> Extracting archive to: %s", target_path)

                if download_destination.endswith(".zip") or should_unpack == "zip":
                    with zipfile.ZipFile(download_destination, "r") as zip_ref:
                        _safe_zip_extractall(zip_ref, target_path)
                    _logger.info("   Status: Extraction completed successfully (.zip)")

                elif (
                    download_destination.endswith(".tar.gz")
                    or download_destination.endswith(".tgz")
                    or should_unpack == "tgz"
                ):
                    with tarfile.open(download_destination, "r:gz") as tar_ref:
                        _safe_tar_extractall(tar_ref, target_path)
                    _logger.info("   Status: Extraction completed successfully (.tar.gz)")

                else:
                    _logger.warning(
                        "Unknown archive extension for file '%s'. File left in temp.",
                        url_filename,
                    )

            # Clean up the temporary directory and downloaded file
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                _logger.debug("Failed to remove temporary directory %s: %s", temp_dir, e)

    except Exception as e:
        _logger.error("Error during download/extraction: %s", e)


# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Updated input structure with the "unpack" key
    input_data = [
        {
            "os": "Windows",
            "url": "https://example.com",
            "path": "C:\\Program Files\\MyTool",  # Directory where files will be unpacked
            "unpack": True,
        },
        {
            "os": "Linux",
            "url": "https://example.com",
            "path": "/opt/mytool",  # Directory where files will be unpacked
            "unpack": True,
        },
        {
            "os": "Darwin",
            "url": "https://example.com",
            "path": "documents/mac/manual.pdf",  # Direct file path
            "unpack": False,  # Will download directly without unpacking
        },
    ]

    download_and_process_file(input_data)
