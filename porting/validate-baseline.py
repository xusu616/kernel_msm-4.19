import collections,hashlib,json,re,struct,zlib
from pathlib import Path
porting=Path(__file__).resolve().parent
build=Path((porting/"local/baseline-build-path.txt").read_text().strip())
original=Path("/mnt/d/santoni-recovery-bypass/roms/lineage18-boot-original.img").read_bytes()
page=struct.unpack_from("<I",original,36)[0];size=struct.unpack_from("<I",original,8)[0]
a=original[page:page+size];b=(build/"out/arch/arm64/boot/Image.gz-dtb").read_bytes()
def details(data):
 dec=zlib.decompressobj(31);image=dec.decompress(data);dtbs=dec.unused_data
 parts=[]
 while dtbs:
  if dtbs[:4] != b"\xd0\x0d\xfe\xed":
   raise ValueError("Unexpected bytes between appended device trees")
  length=struct.unpack_from(">I",dtbs,4)[0]
  parts.append(hashlib.sha256(dtbs[:length]).hexdigest());dtbs=dtbs[length:]
 dtbs=dec.unused_data
 banner=re.search(rb"Linux version [^\x00\n]+",image).group().decode()
 return dict(linux_banner=banner,dtb_parts=parts,payload_bytes=len(data),image_bytes=len(image),image_sha256=hashlib.sha256(image).hexdigest(),dtb_bytes=len(dtbs),dtb_sha256=hashlib.sha256(dtbs).hexdigest(),dtb_prefix=dtbs[:16].hex())
report=dict(original=details(a),baseline=details(b))
report['dtbs_identical']=report['original']['dtb_sha256']==report['baseline']['dtb_sha256']
report['kernel_identical']=a==b
report['dtb_sets_identical']=collections.Counter(report['original']['dtb_parts'])==collections.Counter(report['baseline']['dtb_parts'])
(build/"comparison.json").write_text(json.dumps(report,indent=2)+"\n")
(porting/"baseline-comparison.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
