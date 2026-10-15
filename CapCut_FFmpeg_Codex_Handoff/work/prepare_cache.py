"""Giải nén RAR bằng bsdtar/7-Zip, kiểm tra tên entry và checksum trước khi chạy."""

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

from inspect_cache import ROOT, resources

EXPECTED = "0ab5b75f72ada6132f7e6dd3812b950934e1608bb724dc98e764978c0503cf47"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "archive",
        nargs="?",
        type=Path,
        default=ROOT.parent / "01_SOURCE_AND_CACHE/capcut_original_effect_cache.rar",
    )
    p.add_argument("--cache", type=Path, default=ROOT / "cache")
    p.add_argument(
        "--allow-other-hash",
        action="store_true",
        help="Chỉ dùng khi đã tự kiểm tra cache thay thế",
    )
    a = p.parse_args()
    archive = a.archive.resolve()
    cache = a.cache.resolve()
    if not archive.is_file():
        p.error(f"Không tìm thấy RAR: {archive}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != EXPECTED and not a.allow_other_hash:
        p.error(f"SHA256 khác gói bàn giao: {digest}")
    try:
        resources(cache)
    except (FileNotFoundError, StopIteration):
        pass
    else:
        print("Cache đã sẵn sàng; không ghi đè.")
        return
    tar = shutil.which("tar")
    if not tar:
        p.error("Cần bsdtar hỗ trợ RAR (tar.exe có sẵn trên Windows 11)")
    listing = subprocess.run(
        [tar, "-tf", str(archive)], capture_output=True, text=True, check=True
    ).stdout
    for entry in listing.splitlines():
        normalized = entry.replace("\\", "/")
        relative = PurePosixPath(normalized)
        if (
            relative.is_absolute()
            or PureWindowsPath(normalized).drive
            or ".." in relative.parts
        ):
            p.error(f"Entry vượt thư mục cache: {entry}")
        destination = (cache / normalized).resolve()
        if not destination.is_relative_to(cache):
            p.error("Entry vượt thư mục cache")
    cache.mkdir(parents=True, exist_ok=True)
    subprocess.run([tar, "-xf", str(archive), "-C", str(cache)], check=True)
    resources(cache)
    print(f"Đã giải nén {len(listing.splitlines())} entries; SHA256={digest}")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    main()
