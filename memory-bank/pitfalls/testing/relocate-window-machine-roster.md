# 真机 relocate 收尾实验: daemon 全机名册判据遇生产实例在跑, 离线窗永不开(测试接缝旁路需授权)

> 摘要: 真机 relocate 收尾实验: daemon 全机名册判据遇生产实例在跑, 离线窗永不开(测试接缝旁路需授权)
> 触发: 收尾窗, 离线窗, daemon 开窗, 全机名册, _spawn_daemon, 测试接缝, relocate 真机, 生产实例在跑, 旁路授权

**Refs:** memory-bank/tasks/26-11-10-backend-relocate-relpath-finalize.md

## 本篇只回答

真机 relocate 收尾实验(需 daemon 离线窗)在本机「生产 qB 实例常驻在跑」条件下为什么等不到开窗,以及经授权的测试侧旁路怎么做。窗判据本身的产品语义看 `tools/recycle_daemon.py`(`_proc_absent` docstring, N1 铁律), 本篇不复述。

### 生产 qB 常驻在跑时, 真机 relocate 实验的 daemon 离线窗永远开不了

- **触发**: 本机跑 relocate 真机实验(arm 后等离线窗改写), 而同机生产 qB 实例(16585/26586)常驻运行 —— daemon 进窗判据证一 = **全机 qbittorrent.exe 名册**(tasklist 分不出实例, 多实例保守面, 产品有意设计): 名册见任一 qB(含生产)⇒ 判「进程在」⇒ 离线窗永不开, 实验卡死在等窗(2026-11-10 E2c 复验实测)。
- **判别**: daemon 恒不进窗而测试实例确已 `real.down`(端口拒连成立);tasklist 见生产 qbittorrent.exe 在跑即为根因。
- **处置**: **先停手要用户显式授权**(旁路放宽的是 N1 防线的实例粒度, 非常规操作), 授权后走产品自留测试接缝: `relocate_exec._spawn_daemon`(docstring 明示「测试替换本方法」)在实验内替换为测试 wrapper 拉起 daemon, **仅在其进程内**把名册窄化为镜像路径级(只认 `D:\Programs\qBittorrent-testing*` 前缀), 端口拒连 + 30s 稳定窗两证保持产品原样; 盘上产品代码零改动, 生产实例与其文件零触碰(tasklist 只读识别不算触碰)。参考实现: `tests-real/tools/daemon_window_wrapper.py`(收编入库耐久化 —— 原件在 E2c 实验 scratch `tests-real/.work/e2c_recheck/`, gitignored 可被 real.seed clean 清掉, 2026-11-10 收编, 唯一改动 = 决策留痕落点移到 `.work/tools-daemon-wrapper/`; E2c 复验实证: qB 在线判 absent=False 零进窗, 双测试实例下线后正确排除生产 2 进程开窗)。授权记录落实验 evidence 目录留痕。
- **守阵**: 无机检(授权面是人工闸)。
