#!/usr/bin/env python3
"""Download the original AOSP Clang 11 toolchain into the WSL build cache."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request
import sys

CACHE = Path("/home/xvsu/satoni-build-cache/toolchains")
URL = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/refs/heads/android11-qpr3-release/clang-r383902b1.tar.gz"
TREE = "1c7dcc2e7095197f7a05dff22a875b6b02ed7117"
EXPECTED_SHA256 = "74e78e8fc2bd6d211806ee098393c68761c642d8b1f0208e0cda9542b360117e"

if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / "clang-r383902b1.tar.gz"
    destination = CACHE / "clang-r383902b1"
    if (destination / "bin/clang").exists():
        version = subprocess.check_output([str(destination / "bin/clang"), "--version"], text=True)
        if "Android (6877366 based on r383902b1) clang version 11.0.2" not in version:
            raise RuntimeError("Existing toolchain does not match the recorded ROM compiler")
        if archive.exists():
            size = archive.stat().st_size
            archive.unlink()
            print("Removed extracted download archive:", size, "bytes")
        print(version)
        sys.exit(0)
    if not archive.exists():
        temporary = archive.with_suffix(".part")
        print("Downloading AOSP clang-r383902b1", flush=True)
        with urllib.request.urlopen(URL, timeout=90) as source, temporary.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        temporary.replace(archive)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError("AOSP toolchain archive hash mismatch")
    destination.mkdir(exist_ok=True)
    print("Extracting toolchain", flush=True)
    with tarfile.open(archive) as source:
        source.extractall(destination, filter="data")
    version = subprocess.check_output([str(destination / "bin/clang"), "--version"], text=True)
    print(version, flush=True)
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    metadata = dict(url=URL, tree=TREE, archive_sha256=digest, clang_version=version)
    (CACHE / "clang-r383902b1.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Archive SHA256:", digest)
    archive.unlink()
