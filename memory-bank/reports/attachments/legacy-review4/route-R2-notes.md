# R2 路线小结(存量评审 R4 · config·rules·infra)

owner: clone2-main · freeze: f088329291e6 · 快照: D:\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone2
终态: 6/6 批完成 · findings 共 47 条全部过引文校验(major 2 / minor 33 / nit 12) · refute 0

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R2-1 | 校验面 config/validation ≈2.3K | 10 (minor 7 / nit 3) | done |
| R2-2 | schema 与装载 ≈2.5K | 4 (minor 3 / nit 1) | done |
| R2-3 | 写入与迁移 ≈1.9K | 4 (minor 4) | done |
| R2-4 | rules 全域 ≈3.4K | 11 (major 1 / minor 8 / nit 2) | done |
| R2-5 | infra 存储 ≈1.4K | 6 (major 1 / minor 5) | done |
| R2-6 | infra 工具 ≈1.9K | 12 (minor 8 / nit 4) | done |

major 2 条(S6 聚合会话呈报拍板用)——
1. rules/conditions.py:171 HrCondition 未识别 mode 静默落入 condition-met 分支(拼写错误能过加载、行为随站点配置漂移、无诊断,违反 fail-fast)。
2. infra/file_access.py:212 LocalFileAccess.scandir 的 UNC 路径经归一双斜杠被压掉后当相对路径拼 cwd,Windows 宿主 + UNC save_path 时目录浏览/迁移扫描打开错误路径。

## R2 复验结论

- **D-01 已消失**: sections.py `_validate_qbittorrent` 已补三 str 键类型检查(260-262 行,与 web.token 同形态,注释自证 26-10 修复);loaders.py:93-101 侧同为纯字段透传无日志/回显。
- **C-02 已消失**: 底册锚实为 src/auto_qb/core/curves.py:76(非 config/validation/curves.py),签名已显式 Optional,RUF013 不再成立。
- **GH-01 已消失**: relocate_journal.py 头注已改口径明说「两个写者」且都走 write_journal 前向合并;relocate_mod.py 写点已不存在(收敛至 relocate_exec.py 与 tools/finalize_watch.py),头注与实际一致。

## 自弃发现记录

- 引文校验 refute 0:47/47 全过,无自弃。
- reviewer 主动不报(有据可查的候选排除):base.py `_POLICY_STOP` 未引用但注释明示作「注释锚点」用途;dry-run 下 state.setdefault 仅内存变异无落盘;locking.release 在未持有时删 meta 文件(仓内唯一调用方不会走到);atomic_write POSIX 目录级 fsync 缺失(理论面,Windows 主场);schema __init__ KNOWN_*/枚举重导出(刻意兼容面,tests/ 有导入)。

## 执行备注(供 S6 聚合会话参考)

- **review.check 快照用法缺陷(S0 工具问题,建议入池)**: `review.check --root <快照目录>` 被 `_resolve_root` 的 `.git` 存在性检查拒收(缺 .git 即 die),与命令 help 明文的存量用法矛盾;实际 `_verify` 直接从 root 读文件比对,与 git 无关,检查是误伤。R2 全程走等价通路:每批先 `git diff --stat f088329291e6..HEAD -- <批文件>` 确认零变更后,对工作树根(默认 root)跑校验,语义与快照比对等价(本轮快照 freeze 后 HEAD 无任何 R2 批内文件变更,等价性成立)。
- 面拆分:R2-1/2/3/5/6 两面(正确性+安全 / 测试缺口+文档漂移),R2-4(3372 行最大批)三面(正确性 / 安全 / 测试缺口+文档漂移),串行派遣无并发。
- 面2 各批均核实 tests/ 覆盖扎实(TMPDIR/测试计划清单零违规),仅 R2-1 出 1 条测试缺口(gtm provider 分支零覆盖)与 R2-5 出 1 条(_is_mount_point 正向识别零覆盖)。
