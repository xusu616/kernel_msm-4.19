#!/usr/bin/env python3
"""Build the port over the validated baseline, keeping all outputs in WSL."""
import argparse,json,os,shutil,subprocess
from pathlib import Path

PORTING=Path(__file__).resolve().parent
CACHE=Path("/home/xvsu/satoni-build-cache")
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs",type=int,default=16)
    parser.add_argument("--susfs",action="store_true")
    args=parser.parse_args()
    root=Path((PORTING/"local/baseline-build-path.txt").read_text().strip())
    source,output=root/"kernel",root/"out"
    saved=CACHE/"baseline-artifacts"
    if not saved.exists():
        saved.mkdir()
        for name in ["arch/arm64/boot/Image.gz-dtb","Module.symvers","System.map",".config"]:
            target=saved/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(output/name,target)
        for module in output.rglob("*.ko"):
            target=saved/module.relative_to(output);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(module,target)
    for name in json.loads((PORTING/"source-files.json").read_text()):
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PORTING.parent/name,target)
    shutil.copytree(PORTING.parent/"drivers/kernelsu",source/"drivers/kernelsu",dirs_exist_ok=True)
    shutil.copy2(PORTING/"baseline.config",output/".config")
    fragment="ksun-susfs.config" if args.susfs else "ksun-legacy.config"
    config=(PORTING.parent/"arch/arm64/configs/vendor/feature"/fragment).read_text()
    with (output/".config").open("a") as stream:stream.write("\n"+config)
    env=os.environ.copy();env["LC_ALL"]="C";env["PATH"]=str(CACHE/"toolchains/clang-r383902b1/bin")+":"+str(CACHE/"host-tools/usr/bin")+":"+env["PATH"]
    env.update(KBUILD_BUILD_USER="xvsu",KBUILD_BUILD_HOST="santoni-build",KBUILD_BUILD_VERSION="3")
    command=["make","-C",str(source),"O="+str(output),"ARCH=arm64","LLVM=1","LLVM_IAS=1",
             "CLANG_TRIPLE=aarch64-linux-gnu-","CROSS_COMPILE=aarch64-linux-gnu-","CROSS_COMPILE_COMPAT=arm-linux-gnueabi-",
             "HOSTCC=clang","HOSTCXX=clang++"]
    stage="susfs" if args.susfs else "next"
    log=root/("build-"+stage+".log")
    print("Stage:",stage,"Log:",log,flush=True)
    with log.open("w") as stream:
        result=subprocess.run(command+["olddefconfig"],env=env,stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode==0:
            result=subprocess.run(command+["-j"+str(args.jobs),"Image.gz-dtb","modules"],env=env,stdout=stream,stderr=subprocess.STDOUT)
    print("Result:",result.returncode,flush=True)
    if result.returncode:print("".join(log.read_text(errors="replace").splitlines(True)[-85:]))
    raise SystemExit(result.returncode)
