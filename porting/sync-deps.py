#!/usr/bin/env python3
"""Fetch exactly the external commits in dependencies.json into the WSL cache."""
import concurrent.futures
import json
from pathlib import Path
import subprocess

PORTING = Path(__file__).resolve().parent
SOURCES = Path("/home/xvsu/satoni-build-cache/sources")


def fetch(project):
    repo = SOURCES / project["name"]
    if not repo.exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", "--single-branch",
                        "--branch", project["branch"], project["url"], str(repo)], check=True)
    commit = project["commit"]
    present = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", commit + "^{commit}"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if present.returncode:
        subprocess.run(["git", "-C", str(repo), "fetch", "--depth=1", "origin", commit], check=True)
    print(project["name"] + ": " + commit, flush=True)


if __name__ == "__main__":
    SOURCES.mkdir(parents=True, exist_ok=True)
    projects = json.loads((PORTING / "dependencies.json").read_text())["projects"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(fetch, projects))
