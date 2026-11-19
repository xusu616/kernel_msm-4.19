#!/usr/bin/env python3
"""Assemble the original kernel and pinned external trees on a Linux filesystem.
Git archive preserves case-colliding names and symlinks absent from the Windows
editing checkout. This prepares an unmodified baseline, not a ported kernel.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

PORTING = Path(__file__).resolve().parent
REPO = PORTING.parent


def extract(repo, commit, destination, prefix=""):
    destination.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(["git", "-C", str(repo), "archive", "--prefix=" + prefix, commit], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            archive.extractall(destination, filter="data")
    finally:
        process.stdout.close()
        status = process.wait()
    if status != 0:
        raise RuntimeError(f"git archive failed: {repo} @ {commit}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, default=Path("/home/xvsu/satoni-build-cache"))
    args = parser.parse_args()
    baseline = json.loads((PORTING / "baseline.json").read_text())
    dependencies = json.loads((PORTING / "dependencies.json").read_text())
    args.parent.mkdir(parents=True, exist_ok=True)
    build_root = Path(tempfile.mkdtemp(prefix="santoni-kernel-baseline-", dir=args.parent)).resolve()
    source = build_root / "kernel"
    print(f"Build directory: {build_root}", flush=True)
    extract(REPO, baseline["kernel_commit"], source)
    for project in dependencies["projects"]:
        print(f"Extracting {project['name']} @ {project['commit']}", flush=True)
        extract(args.parent / "sources" / project["name"], project["commit"], source, project["destination"] + "/")
    output = build_root / "out"
    output.mkdir()
    shutil.copyfile(PORTING / "baseline.config", output / ".config")
    local = PORTING / "local"
    local.mkdir(exist_ok=True)
    (local / "baseline-build-path.txt").write_text(str(build_root) + "\n")
    (build_root / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n")
    (build_root / "dependencies.json").write_text(json.dumps(dependencies, indent=2) + "\n")
    print(f"Source: {source}")
    print(f"Output: {output}")
    print("External dependency revisions are candidates; compare generated DTBs and modules before flashing.")


if __name__ == "__main__":
    main()
