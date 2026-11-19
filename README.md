# Redmi 4X（santoni）4.19：Next Legacy + SUSFS

基于 [Mi-Thorium/kernel_msm-4.19](https://github.com/Mi-Thorium/kernel_msm-4.19)，对应本机 LineageOS 18.1 / Android 11。
原 ROM 为 `lineage-18.1-20260524-UNOFFICIAL-Mi8937_4_19.zip`，内核基线提交为 `2ccb48e636087005ada81441a24d67029abc8c5d`。

## 实机结果

2026-11-19 已刷入 Redmi 4X 并重启验证：

- 运行新编译的 `4.19.325-cip132-st16-Mi8937v2-g2ccb48e63608 #3`，启动完成。
- Next 驱动：`v3.4.0-legacy-susfs-v2 (33225-4)`，管理器显示“工作中”。
- 官方管理器与 ksud 为 3.4.0 / API 4；Shell 的 `su -c id` 实测 UID 0、`u:r:ksu:s0`。
- SUSFS 客户端返回 `v2.2.0 / NON-GKI`，列出九项内核功能。
- SELinux 实际 enforcing 状态为 `1`。
- 基线、Next、Next + SUSFS 均已完整编译通过；两种移植构建相对复现基线的导出符号 CRC 未变。

官方 3.4.2 管理器也已测试：其版本为 `33355-5`，要求 API 5；当前驱动为 API 4，会出现 `Kernel update required`。已保留数据恢复匹配的 3.4.0。
升级管理器 APK 本身不需要重打包 boot；如果新管理器要求新的内核 API，则需要同步更新驱动实现。修改 Next / SUSFS 内核代码后才需重新编译、打包和追加 Appender。

## 源码、工具和缓存的位置

| 内容 | 位置 | 是否提交到 Git |
| --- | --- | --- |
| 源码、配置、脚本和说明 | `D:\Project\kernel_msm-4.19` | 是 |
| 便携 Clang 11.0.2 | `/home/xvsu/satoni-build-cache/toolchains/clang-r383902b1` | 否 |
| Git 依赖下载缓存 | `/home/xvsu/satoni-build-cache/sources` | 否 |
| Linux 构建树、对象文件和日志 | `/home/xvsu/satoni-build-cache` | 否 |
| 镜像、模块包、APK 与实机报告 | 仓库的 `artifacts/` | 否，已忽略 |
| 完整 boot 备份与刷入记录 | 仓库的 `backups/` | 否，已忽略 |
| 本机临时状态 | `porting/local/` | 否，已忽略 |

Clang 是从 AOSP 归档解压使用的工具链，不需要安装到系统目录。可直接查看版本：

```powershell
wsl -e /home/xvsu/satoni-build-cache/toolchains/clang-r383902b1/bin/clang --version
```

版本字符串与原 ROM 完全匹配：Android 6877366 / r383902b1 / Clang 11.0.2。归档 SHA256 为 `74e78e8fc2bd6d211806ee098393c68761c642d8b1f0208e0cda9542b360117e`。
准备脚本校验后会删除已解压的下载归档，保留便携目录。系统 Clang 23 及仅供它使用的 clang-libs 已按用户要求卸载。

D 盘检出用于编辑，存在大小写冲突和 Windows 保留文件名的目录使用稀疏检出。实际构建从 Git 对象恢复完整 Linux 源码、大小写不同的全部文件和真正的符号链接，放在 WSL 文件系统中。

## 从缓存为空开始构建

需要 WSL `archlinux`，以及 Git、Python 3.14+、make、flex、bison 和主机 C 构建基础环境。
在 `/mnt/d/Project/kernel_msm-4.19` 执行：

```sh
python3 porting/sync-deps.py
python3 porting/setup-toolchain.py
python3 porting/setup-host-tools.py
python3 porting/prepare-baseline.py
python3 porting/build-baseline.py --jobs 16
python3 porting/validate-baseline.py
python3 porting/build-next.py --jobs 16
python3 porting/save-stage.py next
python3 porting/build-next.py --susfs --jobs 16
python3 porting/save-stage.py susfs
```

`sync-deps.py` 严格使用 `porting/dependencies.json` 中的固定提交。最初按原 ROM 构建时间追溯选定，重建不会再按日期选择新提交。
`baseline.config` 是从原 boot 内嵌配置提取的完整配置；`source-files.json` 记录相对原基线叠加的源码。内核中的 Next 驱动已经包含在 `drivers/kernelsu/`，无须再次拉取它才能构建。

这些命令使用 Clang 11 工具链和本地缓存的 bc，不需要系统安装 Clang 23。
构建日志位于缓存的 `santoni-kernel-baseline-*/build-*.log`。原内核尚未实现逐字节复现；七个 DTB 已分别与原 ROM 逐字节比较一致，仅拼接顺序不同。

## boot 打包与 Appender

**本机依赖锁定 bootloader 的启动验证绕过，最终 boot 必须带 Appender。**
`porting/package-boot.py` 在完成所有内核替换与打包后，最后追加已实测的 4096 字节尾块。
它正确更新这份 ROM 的 legacy boot ID，保留原 ROM ramdisk、命令行和地址布局，验证设备树及镜像大小。
`check-package.py` 已验证原内核可逐字节还原原 boot；追加结果与此前实测成功的 appended boot 完全一致，重复处理不会叠加第二份尾块。

准备同一 ROM 的原始 `boot.img`，SHA256 必须为：

```text
3f3ee4069122657077ee114e2de88353aa58537a9cb65daf071c75e971bd147b
```

标准 ROM 设备树配置的打包：

```sh
python3 porting/check-package.py
python3 porting/package-boot.py --stage next --original /path/to/lineage18-boot-original.img
python3 porting/package-boot.py --stage susfs --original /path/to/lineage18-boot-original.img
```

其中 `check-package.py` 的本机测试输入位于 `D:\santoni-recovery-bypass\roms`，另一台电脑需要先提供同一原始和已验证 appended 镜像。

本机此前的运行镜像还有 CPU 频率表和 CPR corner 修改。本次实机测试保留了从完整 boot 备份提取的现有设备树，频率表包含 1497600 / 1209600 kHz，保留 corner 7。未新增其他超频设置：

```sh
python3 porting/extract-phone-dtbs.py --boot /path/to/verified-boot-backup.img --output artifacts/current-phone-dtb-tail.bin
python3 porting/package-boot.py --stage susfs --original /path/to/lineage18-boot-original.img --dtb-tail artifacts/current-phone-dtb-tail.bin
```

实机刷入文件：`artifacts/boot-santoni-ksun-legacy-susfs-current-dtbs-appended.img`，21616640 字节，SHA256：

```text
b977ad2682d3617d827cf0c79417ccf32cc685fc3858d54e1baf6046084e181d
```

## 备份、刷入和恢复

本次顺序为：备份当前整个 64 MiB boot 分区到电脑并校验 → 安装匹配管理器 → 确认恢复分区尾块 → 写入 boot → 读回逐字节核对 → 重启验证。
原 boot 完整备份的 SHA256 为：

```text
20350cffc6c15fde5cdbf967b4d3137beb41496bf9a790f03428722f9644cdaf
```

备份与设备信息位于 `backups/boot-before-ksun-susfs-*.img` 及对应 JSON；读回副本和刷入记录也在该目录。
`porting/backup-phone-boot.py` 和 `porting/flash-phone-boot.py` 都要求明确传入 ADB 路径与序列号；刷入还要求已验证备份清单，只写 boot 并验证读回。

如需恢复，在已验证的 TWRP 中把电脑上的完整原 boot 备份写回 **Boot**，按备份 JSON 核对分区及哈希。无需格式化数据。

## 清理缓存

停止构建并确认交付文件已复制到 D 盘后，可以删除专用缓存：

```powershell
wsl -e rm -rf /home/xvsu/satoni-build-cache
```

这会删除工具链、依赖下载和 Linux 构建目录。再次构建需重新执行准备步骤；D 盘源码、`artifacts/` 和 `backups/` 不在删除范围内。

## 验证范围

已验证启动、管理器识别、Shell root、SELinux 状态与 SUSFS 版本/九项功能查询。尚未逐项验证全部隐藏行为和长期稳定性。
实机日志观察到三条早期 GIC 警告，对应 `irq-gic.c` 的 `IRQ_TYPE_NONE` 检查。相关 IRQ 源码和当前设备树的中断属性没有修改，警告早于 KSU/SUSFS 初始化；本次未处理该独立问题。未观察到 Kernel panic / Oops。
原始运行记录和设备截图保存在被 Git 忽略的 `artifacts/runtime/`。

## Remotes

- `upstream`: `https://github.com/Mi-Thorium/kernel_msm-4.19.git`
- `github`: `git@github.com:xusu616/kernel_msm-4.19.git`
- `gitlab`: `git@gitlab.com:xusu616/kernel_msm-4.19.git`，导入状态由用户的 GitLab 项目决定。

上游 Linux 说明保留在原 `README` 文件中。具体接口适配原因见 `porting/PORTING-NOTES.md`。
