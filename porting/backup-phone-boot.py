#!/usr/bin/env python3
"""Back up the connected santoni boot partition to Windows and verify both ends."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib,json,shlex,subprocess
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--adb",type=Path,required=True)
parser.add_argument("--serial",required=True)
parser.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent.parent/"backups")
args=parser.parse_args();adb=[str(args.adb),"-s",args.serial]
def shell(command):
 return subprocess.check_output(adb+["shell",command],text=True,timeout=30).strip()
def root(command):return shell("su -c "+shlex.quote(command))
if shell("getprop ro.product.device")!="santoni":raise RuntimeError("Connected device is not santoni")
identity=root("id")
if not identity.startswith("uid=0("):raise RuntimeError("Magisk root is required to read the boot partition")
partition="/dev/block/bootdevice/by-name/boot"
resolved=root("readlink -f "+partition)
size=int(root("blockdev --getsize64 "+partition))
if size!=67108864:raise RuntimeError("Unexpected santoni boot partition size")
before=root("sha256sum "+partition).split()[0]
time=datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d-%H%M%S")
args.output_dir.mkdir(parents=True,exist_ok=True)
target=args.output_dir/("boot-before-ksun-susfs-"+time+"-"+args.serial+".img")
print("Backing up:",target,flush=True)
with target.open("xb") as output:
 subprocess.run(adb+["exec-out","su -c "+shlex.quote("cat "+partition)],stdout=output,check=True,timeout=90)
with target.open("rb") as source:digest=hashlib.file_digest(source,"sha256").hexdigest()
after=root("sha256sum "+partition).split()[0]
if target.stat().st_size!=size or not (before==digest==after):
 raise RuntimeError("Backup size or SHA256 verification failed; do not flash")
report=dict(device="santoni",serial=args.serial,boot_partition=resolved,backup=str(target),
            bytes=size,sha256=digest,remote_before=before,remote_after=after,uname=shell("uname -a"))
target.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
(Path(__file__).resolve().parent/"local/phone-boot-backup.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
