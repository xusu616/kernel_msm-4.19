#!/usr/bin/env python3
"""Flash only santoni boot after validating a complete, unchanged PC backup."""
import argparse
from datetime import datetime, timedelta, timezone
import gzip,hashlib,json,runpy,shlex,struct,subprocess,zlib
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--adb",type=Path,required=True)
parser.add_argument("--serial",required=True)
parser.add_argument("--image",type=Path,required=True)
parser.add_argument("--backup-manifest",type=Path,required=True)
args=parser.parse_args();adb=[str(args.adb),"-s",args.serial]
backup=json.loads(args.backup_manifest.read_text())
module=runpy.run_path(str(Path(__file__).with_name("package-boot.py")))
image=args.image.read_bytes();digest=hashlib.sha256(image).hexdigest()
page,parts,end=module["parse_boot"](image)
if image[end:]!=module["FOOTER"] or image[576:608]!=module["image_id"](parts):
 raise RuntimeError("Image must have its valid legacy ID and tested Appender footer")
if len(image)>module["PARTITION_SIZE"]:raise RuntimeError("Image is too large")
decoder=zlib.decompressobj(31);kernel=decoder.decompress(parts[0]);start=kernel.index(b"IKCFG_ST")+8;finish=kernel.index(b"IKCFG_ED",start);config=gzip.decompress(kernel[start:finish]).decode()
for option in ["CONFIG_KSU=y","CONFIG_KSU_MANUAL_HOOK=y","CONFIG_KSU_SUSFS=y"]:
 if option not in config.splitlines():raise RuntimeError("Required option missing: "+option)
with Path(backup["backup"]).open("rb") as source:
 local_backup=hashlib.file_digest(source,"sha256").hexdigest()
if local_backup!=backup["sha256"] or Path(backup["backup"]).stat().st_size!=67108864:
 raise RuntimeError("The complete PC boot backup is missing or changed")
def shell(command):return subprocess.check_output(adb+["shell",command],text=True,timeout=45).strip()
def root(command):return shell("su -c "+shlex.quote(command))
if args.serial!=backup["serial"] or shell("getprop ro.product.device")!="santoni":raise RuntimeError("Device identity mismatch")
if not shell("pm path com.rifsxd.ksunext").startswith("package:"):raise RuntimeError("Install KernelSU Next manager first")
partition="/dev/block/bootdevice/by-name/boot"
if root("readlink -f "+partition)!=backup["boot_partition"]:raise RuntimeError("Boot partition target changed")
if root("sha256sum "+partition).split()[0]!=backup["sha256"]:raise RuntimeError("Current boot changed after the verified backup")
# Confirm recovery still has the bypass footer before changing boot.
command="dd if=/dev/block/bootdevice/by-name/recovery bs=2048 count=1 status=none"
header=subprocess.check_output(adb+["exec-out","su -c "+shlex.quote(command)],timeout=30)
if header[:8]!=b"ANDROID!":raise RuntimeError("Unexpected recovery header")
rpage=struct.unpack_from("<I",header,36)[0]
rend=rpage+sum((struct.unpack_from("<I",header,o)[0]+rpage-1)//rpage*rpage for o in (8,16,24))
command=f"dd if=/dev/block/bootdevice/by-name/recovery bs=2048 skip={rend//2048} count=2 status=none"
footer=subprocess.check_output(adb+["exec-out","su -c "+shlex.quote(command)],timeout=30)
if footer!=module["FOOTER"]:raise RuntimeError("Recovery Appender footer did not match; inspect rollback access first")
remote="/data/local/tmp/santoni-ksun-susfs-appended.img"
subprocess.run(adb+["push",str(args.image),remote],check=True,timeout=90)
if shell("sha256sum "+remote).split()[0]!=digest:raise RuntimeError("Staged image SHA256 mismatch")
print("Writing verified image",args.image,"SHA256",digest,flush=True)
print(root("dd if="+remote+" of="+partition+" bs=4096 conv=fsync"),flush=True)
stamp=datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d-%H%M%S")
readback=args.backup_manifest.parent/("boot-after-flash-prefix-"+stamp+".img")
command=f"dd if={partition} bs=2048 count={len(image)//2048} status=none"
with readback.open("xb") as output:
 subprocess.run(adb+["exec-out","su -c "+shlex.quote(command)],stdout=output,check=True,timeout=90)
if readback.read_bytes()!=image:raise RuntimeError("Boot readback mismatch; do not reboot")
report=dict(serial=args.serial,original_backup=backup["backup"],image=str(args.image),image_sha256=digest,
            written_bytes=len(image),readback=str(readback),readback_verified=True,recovery_footer_verified=True)
args.backup_manifest.with_name("flash-next-susfs-"+stamp+".json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2),flush=True)
print("Rebooting the verified image",flush=True)
subprocess.run(adb+["reboot"],check=True,timeout=20)
