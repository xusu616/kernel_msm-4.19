#!/usr/bin/env python3
"""Extract the current DTB profile from a complete boot-partition backup."""
import argparse,hashlib,runpy,struct
from pathlib import Path

helpers=runpy.run_path(str(Path(__file__).with_name("package-boot.py")))
def extract(data):
    if data[:8]!=b"ANDROID!":raise ValueError("Not an Android boot image")
    page=struct.unpack_from("<I",data,36)[0]
    end=page+sum((struct.unpack_from("<I",data,o)[0]+page-1)//page*page for o in (8,16,24))
    _,parts,_=helpers["parse_boot"](data[:end])
    _,trees=helpers["split_kernel"](parts[0])
    return b"".join(trees)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--boot",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    dtbs=extract(args.boot.read_bytes())
    with args.output.open("xb") as stream:stream.write(dtbs)
    print(hashlib.sha256(dtbs).hexdigest(),args.output)
