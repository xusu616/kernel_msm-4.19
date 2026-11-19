# santoni 移植资料

工具链路径、固定依赖、构建、清理、Appender、备份和实机结果见根目录 [README.md](../README.md)。

- `baseline.json` / `baseline.config`：原 ROM 的版本、编译器和提取配置。
- `dependencies.json`：九项外部依赖的固定提交。
- `source-files.json`：叠加到原基线的源码列表；Next 驱动目录单独整体复制。
- `susfs-source.json`：SUSFS 2.2.0 参考回移来源。
- `PORTING-NOTES.md`：接口差异与修改原因。
- `next-build-report.json` / `susfs-build-report.json`：构建与导出符号 CRC 对比。

所有工具链和依赖下载缓存位于 `/home/xvsu/satoni-build-cache`。
设备状态、镜像和备份分别位于被 Git 忽略的 `local/`、仓库根目录 `artifacts/`、`backups/`。
