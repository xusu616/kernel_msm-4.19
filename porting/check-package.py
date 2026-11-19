import hashlib,runpy,struct
from pathlib import Path
module=runpy.run_path(str(Path(__file__).with_name("package-boot.py")))
original=Path("/mnt/d/santoni-recovery-bypass/roms/lineage18-boot-original.img").read_bytes()
_,parts,_=module["parse_boot"](original)
rebuilt=module["replace_kernel"](original,parts[0])
assert rebuilt==original,"Repacking the original kernel must reproduce the whole original boot"
appended=module["append_footer"](rebuilt)
known=Path("/mnt/d/santoni-recovery-bypass/roms/lineage18-boot-appended.img").read_bytes()
assert appended==known,"Appender output must reproduce the already tested image"
assert module["append_footer"](appended)==appended,"Appender must not add a second footer"
print("PASS: byte-exact original boot round trip, tested Appender image, no duplicate footer")
print(hashlib.sha256(appended).hexdigest())
