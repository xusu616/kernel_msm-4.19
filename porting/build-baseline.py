#!/usr/bin/env python3
"""Build the original santoni kernel using the recovered configuration."""
import argparse
import difflib
import json
import os
from pathlib import Path
import subprocess

PORTING = Path(__file__).resolve().parent
CACHE = Path("/home/xvsu/satoni-build-cache")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=16)
    args = parser.parse_args()
    root = Path((PORTING / "local/baseline-build-path.txt").read_text().strip())
    source, output = root / "kernel", root / "out"
    baseline = json.loads((PORTING / "baseline.json").read_text())
    (source / ".scmversion").write_text("-g" + baseline["kernel_commit"][:12] + "\n")
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    toolchain = CACHE / "toolchains/clang-r383902b1/bin"
    env["PATH"] = str(toolchain) + ":" + str(CACHE / "host-tools/usr/bin") + ":" + env["PATH"]
    env.update(KBUILD_BUILD_USER="nobody", KBUILD_BUILD_HOST="android-build", KBUILD_BUILD_VERSION="2",
               KBUILD_BUILD_TIMESTAMP="Sun May 24 05:39:34 UTC 2026")
    command = ["make", "-C", str(source), "O=" + str(output), "ARCH=arm64", "LLVM=1", "LLVM_IAS=1",
               "CLANG_TRIPLE=aarch64-linux-gnu-", "CROSS_COMPILE=aarch64-linux-gnu-", "CROSS_COMPILE_COMPAT=arm-linux-gnueabi-",
               "HOSTCC=clang", "HOSTCXX=clang++"]
    print(subprocess.check_output(["clang", "--version"], env=env, text=True).splitlines()[0], flush=True)
    log = root / "build-baseline.log"
    with log.open("w") as stream:
        result = subprocess.run(command + ["olddefconfig"], env=env, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode == 0:
            changes = "".join(difflib.unified_diff((PORTING / "baseline.config").read_text().splitlines(True),
                            (output / ".config").read_text().splitlines(True), fromfile="boot-config", tofile="build-config"))
            (root / "config-diff.txt").write_text(changes)
            print(changes or "Configuration matches recovered boot config", flush=True)
            print("Building Image.gz-dtb and modules; log: " + str(log), flush=True)
            result = subprocess.run(command + ["-j" + str(args.jobs), "Image.gz-dtb", "modules"], env=env,
                                    stdout=stream, stderr=subprocess.STDOUT)
    print("Result:", result.returncode, "Log:", log, flush=True)
    if result.returncode:
        print("".join(log.read_text(errors="replace").splitlines(True)[-60:]))
    raise SystemExit(result.returncode)
