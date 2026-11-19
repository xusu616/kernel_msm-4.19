# 实现与验证记录

原基线、Next Legacy、Next Legacy + SUSFS 均已完整编译通过。移植构建相对基线的导出符号 CRC 未变。实机启动、管理器识别、Shell root、SUSFS 版本和九项功能查询均已通过。

Next Legacy 使用 `drivers/kernelsu/UPSTREAM.md` 中固定的源码。版本号保持上游对应提交按完整 Git 历史计算的值。
Kbuild 不再直接改写内核源码；这棵 4.19 已有 `path_umount`、SELinux accessors。seccomp 没有 `filter_count`，因此仅在确有字段的内核上重置它，不添加没有生命周期维护的假字段。

SUSFS 2.2.0 的参考回移来自 `susfs-source.json` 所记录提交。手工适配内容：

- Mi-Thorium 已回移 fs_context，挂载分配由 vfs_kern_mount 移至 vfs_create_mount；相同逻辑接入实际分配位置。
- 保留本树 proc_command_line 对启动参数的原有处理，仅在 SUSFS 配置了替代内容后覆盖输出。
- 保留 mmap_read_lock 等较新接口；远程内存读取在每次跨页迭代重新检查当前 VMA，避免沿用前一个映射。
- uname 的 SUSFS 处理先执行，再保留 Mi-Thorium 对 bpfloader/netd 等进程的既有兼容覆盖。
- 移除 SUSFS 2.2 不再实现的 TRY_UMOUNT 和实验 MEMFD 配置及调用，使用现有 KSU 挂载卸载机制。
- 修复参考 Next fork 中空的 task_work 凭据切换：它没有持久效果，且 work_pending 提前返回会泄漏预分配对象。改为直接 schedule_work；工作本身拥有并恢复其所需凭据。
- 恢复不启用 SUSFS 时 Next Legacy 原本被注释掉的模块挂载卸载调用。

所有阶段的编译通过都不能替代实机启动和授权测试。原 boot 的 Appender 尾块需在最终打包时追加。

## 运行验证

当前驱动是 API 4，匹配官方管理器 3.4.0（33294-4）及 ksud 3.4.0。
官方 3.4.2（33355-5）的哈希与签名正确，但实际运行要求 API 5，显示 Kernel update required；已保留数据恢复匹配版本并验证 root 正常。

刷入镜像明确采用当前手机备份的 DTB 配置；相对原 ROM，只修改了 santoni 的两个 cpufreq 表和 CPR corner 属性。本次保留用户原有设置，没有新增超频配置。

原镜像的 boot ID 使用 SHA1(kernel+size, ramdisk+size, second+size, absent DT size)，最后一个零大小字段不能省略。
打包回环已逐字节还原原镜像及此前实测的 Appender 镜像。闪存写入后读回逐字节一致，再发出重启命令。
