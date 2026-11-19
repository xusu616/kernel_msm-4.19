#!/usr/bin/env python3
"""Repack the known legacy v0 boot, preserve its DTBs, then append Appender."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import zlib

PORTING = Path(__file__).resolve().parent
CACHE = Path("/home/xvsu/satoni-build-cache")
FOOTER = bytes.fromhex("3083198964") + bytes(4091)
PARTITION_SIZE = 64 * 1024 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def parse_boot(data):
    if len(data) < 1632 or data[:8] != b"ANDROID!":
        raise ValueError("Not a complete Android boot image")
    page = struct.unpack_from("<I", data, 36)[0]
    if struct.unpack_from("<I", data, 40)[0] != 0 or page != 2048:
        raise ValueError("Expected this ROM's v0 header and 2048-byte pages")
    position = page
    parts = []
    for offset in (8, 16, 24):
        size = struct.unpack_from("<I", data, offset)[0]
        if position + size > len(data):
            raise ValueError("Truncated boot payload")
        parts.append(data[position:position + size])
        position += (size + page - 1) // page * page
    if position > len(data) or data[position:] not in (b"", FOOTER):
        raise ValueError("Unexpected boot padding or trailing bytes")
    return page, parts, position


def image_id(parts):
    digest = hashlib.sha1()
    for part in parts:
        digest.update(part)
        digest.update(struct.pack("<I", len(part)))
    # This ROM's legacy mkbootimg includes the absent DT-section size as well.
    digest.update(struct.pack("<I", 0))
    return digest.digest() + bytes(12)


def split_kernel(payload):
    decoder = zlib.decompressobj(31)
    decoder.decompress(payload)
    if not decoder.eof:
        raise ValueError("Incomplete gzip-compressed kernel")
    tail = decoder.unused_data
    compressed = payload[:len(payload) - len(tail)]
    trees = []
    while tail:
        if len(tail) < 40 or tail[:4] != bytes.fromhex("d00dfeed"):
            raise ValueError("Invalid appended DTB")
        size = struct.unpack_from(">I", tail, 4)[0]
        if size < 40 or size > len(tail):
            raise ValueError("Truncated appended DTB")
        trees.append(tail[:size])
        tail = tail[size:]
    return compressed, trees


def replace_kernel(original, replacement, dtb_override=None):
    page, parts, end = parse_boot(original)
    if original[576:608] != image_id(parts):
        raise ValueError("Original boot ID does not match the recorded legacy algorithm")
    _, old_trees = split_kernel(parts[0])
    compressed, new_trees = split_kernel(replacement)
    if Counter(map(sha256, old_trees)) != Counter(map(sha256, new_trees)):
        raise ValueError("Compiled DTBs differ from the original ROM; inspect device-tree revisions")
    trees = old_trees
    if dtb_override is not None:
        _, trees = split_kernel(compressed + dtb_override)
        if len(trees) != len(old_trees):
            raise ValueError("Device-specific DTB profile has a different tree count")
    parts[0] = compressed + b"".join(trees)
    header = bytearray(original[:page])
    struct.pack_into("<I", header, 8, len(parts[0]))
    header[576:608] = image_id(parts)
    result = bytes(header)
    for part in parts:
        result += part + bytes((-len(part)) % page)
    return result


def append_footer(boot):
    _, _, end = parse_boot(boot)
    return boot[:end] + FOOTER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["next", "susfs"], required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=PORTING.parent / "artifacts")
    parser.add_argument("--dtb-tail", type=Path, help="Explicit DTB profile extracted from a verified phone backup")
    args = parser.parse_args()
    original = args.original.read_bytes()
    baseline = json.loads((PORTING / "baseline.json").read_text())
    if sha256(original) != baseline["boot_sha256"]:
        raise ValueError("Use the exact original boot from the recorded Android 11 ROM")
    stage = CACHE / (args.stage + "-artifacts")
    kernel = (stage / "arch/arm64/boot/Image.gz-dtb").read_bytes()
    dtb_override = args.dtb_tail.read_bytes() if args.dtb_tail else None
    boot = append_footer(replace_kernel(original, kernel, dtb_override))
    if len(boot) > PARTITION_SIZE:
        raise ValueError("Repacked image exceeds the phone's boot partition")
    page, output_parts, end = parse_boot(boot)
    _, original_parts, _ = parse_boot(original)
    assert output_parts[1:] == original_parts[1:]
    assert boot[:8] == original[:8] and boot[end:] == FOOTER
    assert boot[576:608] == image_id(output_parts)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    name = "boot-santoni-ksun-legacy" + ("-susfs" if args.stage == "susfs" else "")
    if dtb_override is not None:
        name += "-current-dtbs"
    target = args.output_dir / (name + "-appended.img")
    with target.open("xb") as stream:
        stream.write(boot)
    modules = args.output_dir / (name + "-modules.zip")
    with zipfile.ZipFile(modules, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for module in sorted(stage.rglob("*.ko")):
            archive.write(module, "lib/modules/" + module.name)
    report = json.loads((stage / "report.json").read_text())
    report.update(boot_image=target.name, boot_bytes=len(boot), boot_sha256=sha256(boot),
                  original_boot_sha256=sha256(original), footer_bytes=len(FOOTER),
                  original_ramdisk_preserved=True, original_dtb_order_preserved=True,
                  runtime_tested=False, modules_zip=modules.name, modules_zip_sha256=sha256(modules.read_bytes()),
                  boot_kernel_sha256=sha256(output_parts[0]),
                  device_tree_profile=str(args.dtb_tail) if args.dtb_tail else "original ROM",
                  device_tree_tail_sha256=sha256(dtb_override) if dtb_override is not None else None)
    metadata = args.output_dir / (name + ".json")
    with metadata.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
