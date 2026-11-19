#!/usr/bin/env python3
"""Keep the missing bc build utility inside the disposable WSL cache."""
from pathlib import Path
import subprocess
import tarfile
import urllib.request

CACHE = Path("/home/xvsu/satoni-build-cache/host-tools")
if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    urls = subprocess.check_output(["pacman", "-Sp", "--print-format", "%l", "bc"], text=True).splitlines()
    url = next(url for url in urls if "/bc-" in url)
    package = CACHE / url.rsplit("/", 1)[1]
    if not package.exists():
        with urllib.request.urlopen(url, timeout=30) as source, package.open("wb") as target:
            target.write(source.read())
    with tarfile.open(package) as source:
        source.extractall(CACHE, filter="data")
    subprocess.run([str(CACHE / "usr/bin/bc"), "--version"], check=True)
