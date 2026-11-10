# 26-11-11-backend-relocate-bt-backup-probe — 整组移动 BT_backup 收编: 单实例标量化 + 设置页自动探测

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** BT_backup 配置从顶层 host:port 表收编为 relocate.bt_backup 标量(v7→v8 迁移) + 设置页按钮自动探测; 计划已入库(Open), S1-S7 等显式开工
**Topics:** backend-relocate-bt-backup-probe
**Refs:** memory-bank/plans/26-11-11-0259-plan-relocate-bt-backup-scalar-probe.html, memory-bank/pitfalls/ops/msys-container-path.md

## 本篇只回答

BT_backup 配置怎么收编成单实例标量并补设置页自动探测——拍板结论、方案与实施进度在哪; 领域结论(fastresume 收尾机制)在主题文档, 完整方案在计划 26-11-11-0259。

## 原始请求

1. 「BT_backup 的 host:port 应该不用写——目前的设计仅针对主要的 qb, 该功能也不设计跨多个 qb, 所以 BT_backup 仅需要写位置就行了」
2. 「BT_backup 自动探测」
3. 「grilling 然后出一个修改方案」(Q2 补充: 走配置升级路线不做兼容; Q4: 候选集适配多平台/多安装模式/便携; Q7 澄清拍读法2: 探测仅按钮显式触发, 无运行时隐式探测)

## 思考过程与决策

- grilling 三轮九问拍板 D1-D9, 全记录在计划 §06: 核心四条——D1 内嵌 `relocate.bt_backup` 标量(单实例语义进 schema, 认领面收单); D3 探测仅设置页按钮显式触发, 草稿留空 = 未启用(现状语义零破); D7 迁移 v7→v8 恰一条非空则搬运否则删+note; D5 歧义/未命中拒不猜测只列证据。
- 取证(Explore 子代理只读, qB v5.3.0 dev 8182ae07 + libtorrent 2.1.2.0): BT_backup = `SpecialFolder::Data/"BT_backup"` 构造唯一且无 ini 键可改道; Windows 默认布局**无 data\ 中间层**(修正了会话内最初假设); `--configuration` 后缀可从配置目录枚举推导; 便携可探测但需定位 qB exe; `--profile`/`QBT_PROFILE` 不可静态探测 → 手动键兜底; **新发现**: SQLite resume 存储模式下 BT_backup 非主存储, fastresume 改写无效 → 探测标 unusable-sqlite, 与运行面既有 E 格预检(relocate_plan.py:225-239 非 Legacy fail-closed)同口径, 无缺口(评审 R1 轮修正定性)。
- 本机实测: `%APPDATA%\qBittorrent`(默认 profile) + `%LOCALAPPDATA%\qBittorrent\BT_backup` 含大量 fastresume → 探测对本机生产直接有效。

## 实现计划

计划 `memory-bank/plans/26-11-11-0259-plan-relocate-bt-backup-scalar-probe.html` §04: S1 配置面标量化(models/loaders/validation/schema, bt_backup_path_of 改纯读键签名不变) → S2 升级链 v7→v8 + tests-real 14 文件版本 bump(13 测试片 + lib/app.py) → S3 探测后端 infra/bt_backup_probe.py(verdict 五态: hit/ambiguous/miss/unusable-sqlite/manual-set; 不新增依赖, 便携 exe 定位走 PowerShell CIM 或 /proc) → S4 端点 POST /api/relocate/bt_backup_probe + 编辑器单输入+按钮 → S5 运行面口径(认领收单 + 注释) → S6 全量 + 真机按钮验收 → S7 收尾回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 配置面标量化 | Open |
| S2 | 升级链 v7→v8 + tests-real bump | Open |
| S3 | 探测后端 bt_backup_probe.py | Open |
| S4 | 端点 + 编辑器 UI | Open |
| S5 | 运行面口径同步 | Open |
| S6 | 全量测试 + 真机验收(人工) | Open |
| S7 | 收尾回写 + 档案/基线 | Open |

## 进度日志

### R0 · 立档 (2026-11-11)

grilling 三轮九问收敛(D1-D9) + qB/libtorrent 源码取证 + 本机只读实测; 计划 26-11-11-0259 入库(Open); 立档。实施等显式开工。

- 2026-11-11 03:13 grilling 三轮九问拍板 D1-D9 + qB 源码取证 + 计划 26-11-11-0259 入库(Open); BT_backup 收编单实例标量 + 按钮探测; S1-S7 等显式开工
- 2026-11-11 03:47 提交收尾: 分批评审四轮(轮1 计划 6 minor 全修, 含 D8/R1 定性修正——运行面 E 格已 fail-closed 非缺口; 轮2 零新发现; 轮3 分面两路: 面A 零发现, 面B 坑档 1 major(处置④过度概括)采纳修复; 轮4 服务端配额忙, 面B 复核按评审 skill §8 降级主会话自查——零新发现); ship 闸门 vNu 拦出计划 §3.1 一处未闭合 code 标签已修; MSYS 路径转换坑面第三张脸(参数中段 `/xxx`, grep 模式静默零命中)扩进 msys-container-path.md 复发 2
