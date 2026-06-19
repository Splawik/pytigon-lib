import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile


def download_and_process_file(file_list):
    """Detects the current OS, finds the matching item from the list,

    downloads the file (handling large files), and optionally unpacks it.
    """
    # 1. Detect the current operating system
    current_os = platform.system()
    print(f"Detected Operating System: {current_os}")

    # 2. Find the matching row in the provided list
    matched_item = None
    for item in file_list:
        if item.get("os", "").strip().lower() == current_os.lower():
            matched_item = item
            break

    if not matched_item:
        print(
            f"Error: No configuration found for the current OS ({current_os}) in the provided list."
        )
        return

    # 3. Extract configuration data
    url = matched_item.get("url")
    target_path = matched_item.get("path")
    should_unpack = matched_item.get("unpack", False)

    # Determine final file name for download
    # If unpacking, we extract the filename from URL to save it in temp first
    url_filename = url.split("/")[-1] if "/" in url else "downloaded_file"

    if should_unpack:
        # Create a secure temporary directory that is automatically cleaned up
        temp_dir = tempfile.mkdtemp()
        download_destination = os.path.join(temp_dir, url_filename[:64])
        print(f"Matching configuration found (Archive Mode)!")
        print(f" -> URL: {url}")
        print(f" -> Temporary Download Path: {download_destination}")
        print(f" -> Final Extraction Directory: {target_path}")
    else:
        download_destination = target_path
        print(f"Matching configuration found (Direct Download Mode)!")
        print(f" -> URL: {url}")
        print(f" -> Target Path: {download_destination}")

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
            print(f" -> Extracting archive to: {target_path}")

            if download_destination.endswith(".zip") or should_unpack == "zip":
                with zipfile.ZipFile(download_destination, "r") as zip_ref:
                    zip_ref.extractall(target_path)
                print("   Status: Extraction completed successfully (.zip)")

            elif (
                download_destination.endswith(".tar.gz")
                or download_destination.endswith(".tgz")
                or should_unpack == "tgz"
            ):
                with tarfile.open(download_destination, "r:gz") as tar_ref:
                    tar_ref.extractall(target_path)
                print("   Status: Extraction completed successfully (.tar.gz)")

            else:
                print(
                    f"   Status: WARNING - Unknown archive extension for file '{url_filename}'. File left in temp."
                )

            # Clean up the temporary directory and downloaded file
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    except Exception as e:
        sys.stdout.write(f"\n   Status: ERROR occurred: {e}\n")


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
