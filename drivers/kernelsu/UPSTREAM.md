KernelSU Next Legacy, from https://github.com/sidex15/KernelSU-Next
Commit: d999a2aff11575c6e2f520129ecffb7c6058fb02
Tag: v3.4.0-legacy-susfs-v2
Reported version: 30000 + 3025 commits + 200 = 33225 (upstream calculation).

The upstream kernel/ directory is vendored here; root uapi/ headers are in include/uapi/.
Local integration pins the original version, removes build-time source rewriting,
and checks whether seccomp.filter_count actually exists before resetting it.
The 4.19 seccomp implementation has no such counter and does not need a synthetic field.
The kernel driver is GPL-2.0-only; see the upstream project license declaration.
Whitespace and line endings are normalized locally.
