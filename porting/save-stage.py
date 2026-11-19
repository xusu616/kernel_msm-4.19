import argparse,hashlib,json,shutil
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument("stage",choices=["next","susfs"]);args=parser.parse_args()
porting=Path(__file__).resolve().parent;cache=Path("/home/xvsu/satoni-build-cache")
root=Path((porting/"local/baseline-build-path.txt").read_text().strip());out=root/"out"
dest=cache/(args.stage+"-artifacts");dest.mkdir()
for name in ["arch/arm64/boot/Image.gz-dtb","Module.symvers","System.map",".config"]:
 p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(out/name,p)
modules=[]
for module in out.rglob("*.ko"):
 p=dest/module.relative_to(out);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(module,p);modules.append(str(module.relative_to(out)))
def versions(path):
 return {line.split()[1]:line.split()[0] for line in path.read_text().splitlines()}
base=versions(cache/"baseline-artifacts/Module.symvers");now=versions(dest/"Module.symvers")
changed=[name for name,crc in base.items() if now.get(name)!=crc]
report=dict(stage=args.stage,module_count=len(modules),modules=modules,changed_baseline_symbol_crcs=changed,
            image_sha256=hashlib.sha256((dest/"arch/arm64/boot/Image.gz-dtb").read_bytes()).hexdigest())
(dest/"report.json").write_text(json.dumps(report,indent=2)+"\n")
(porting/(args.stage+"-build-report.json")).write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
