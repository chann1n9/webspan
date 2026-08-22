# Usage in Pythonista:
# exec(compile(__import__("requests").get("https://raw.githubusercontent.com/chann1n9/webspan/refs/heads/main/install.py",timeout=15).text,"webspan_install.py","exec"))

from pathlib import Path
import io
import os
import requests
import shutil
import sys
import zipfile


PACKAGE_NAME = "webspan"
REQUEST_TIMEOUT = 15

GH_API = "https://api.github.com/repos/chann1n9/webspan/releases/latest"


def find_install_path():
    """
    Find Pythonista user site-packages directory.
    """
    candidates = []

    for path in sys.path:
        p = Path(path)

        if (
            "site-packages" in str(p)
            and p.exists()
            and os.access(p, os.W_OK)
        ):
            candidates.append(p)

    # Prefer normal user site-packages
    for p in candidates:
        if p.name == "site-packages":
            return p

    if candidates:
        return candidates[0]

    raise RuntimeError(
        "Cannot find writable site-packages directory"
    )


def get_latest_release():
    response = requests.get(
        GH_API,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()

    for asset in data["assets"]:
        if asset["name"].endswith(".whl"):
            print(f"Found wheel: {asset['name']}")
            return asset["browser_download_url"]

    raise RuntimeError("Cannot find wheel in latest release")


def download(url):
    print(f"Downloading: {url}")

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    return response.content


def remove_existing_installation(target):
    package_path = target / PACKAGE_NAME
    metadata_pattern = f"{PACKAGE_NAME}-*.dist-info"

    paths = [
        package_path,
        *target.glob(metadata_pattern),
    ]

    for path in paths:
        if path.is_dir():
            print(f"Removing: {path}")
            shutil.rmtree(path)


def install_wheel(data, target):
    print("Installing to:")
    print(target)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        bad_member = zf.testzip()

        if bad_member is not None:
            raise zipfile.BadZipFile(
                f"Bad CRC for file: {bad_member}"
            )

        package_prefix = f"{PACKAGE_NAME}/"

        if not any(
            member.startswith(package_prefix)
            for member in zf.namelist()
        ):
            raise RuntimeError(
                f"Wheel does not contain {PACKAGE_NAME}"
            )

        remove_existing_installation(target)

        for member in zf.namelist():
            zf.extract(member, target)


def verify():
    import importlib

    module = importlib.import_module(PACKAGE_NAME)

    print()
    print("Installed:")
    print(module.__file__)


def main():
    print("WebSpan Installer")
    print("-" * 30)

    target = find_install_path()

    wheel = download(get_latest_release())

    install_wheel(
        wheel,
        target,
    )

    verify()

    print()
    print("Installation completed.")
    print("Please restart Pythonista.")


if __name__ == "__main__":
    main()
