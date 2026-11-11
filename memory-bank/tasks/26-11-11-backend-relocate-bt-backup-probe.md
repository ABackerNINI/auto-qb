# 26-11-11-backend-relocate-bt-backup-probe — 整组移动 BT_backup 收编: 单实例标量化 + 设置页自动探测

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-12
**Summary:** BT_backup 配置从顶层 host:port 表收编为 relocate.bt_backup 标量(v7→v8 迁移) + 设置页按钮自动探测; S1-S7 全部落地(分批评审全过, 入池 0), 全量基线切片 26-11-11-0756(数字见 kb.baseline); 真机面复测闭环 —— 四判据①②③④全 PASS(切片 26-11-12-0229, 判据③经用户拍板同盘近似拓扑替代), issue 26-11-11-2305 已结
**Topics:** backend-relocate-bt-backup-probe
**Refs:** memory-bank/plans/26-11-11-0259-plan-relocate-bt-backup-scalar-probe.html, memory-bank/pitfalls/ops/msys-container-path.md, memory-bank/issues/26-11-11-2305-test-bt-backup-probe-real-retest.html

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
| S1 | 配置面标量化 | Done (批1 c4ee6149) |
| S2 | 升级链 v7→v8 + tests-real bump | Done (批1 c4ee6149) |
| S3 | 探测后端 bt_backup_probe.py | Done (批2 08b34b54) |
| S4 | 端点 + 编辑器 UI | Done (批3 61363210 + 批4 2e6487e1) |
| S5 | 运行面口径同步 | Done (批5 130ec909) |
| S6 | 全量测试 + 真机验收(人工) | Done: 全量基线切片 26-11-11-0756(数字见 kb.baseline); 真机复测闭环四判据①②③④全 PASS(切片 26-11-12-0229-real-relocate-bt-backup-retest, 判据③经用户拍板同盘近似拓扑替代 RM04-21 钉死拓扑), 原 BLOCKED 段清账(issue 26-11-11-2305 翻 Done) |
| S7 | 收尾回写 + 档案/基线 | Done (R1 本批; 基线切片已入库 f09830e6 / 4281189f) |

## 进度日志

### R0 · 立档 (2026-11-11)

grilling 三轮九问收敛(D1-D9) + qB/libtorrent 源码取证 + 本机只读实测; 计划 26-11-11-0259 入库(Open); 立档。实施等显式开工。

- 2026-11-11 03:13 grilling 三轮九问拍板 D1-D9 + qB 源码取证 + 计划 26-11-11-0259 入库(Open); BT_backup 收编单实例标量 + 按钮探测; S1-S7 等显式开工
- 2026-11-11 03:47 提交收尾: 分批评审四轮(轮1 计划 6 minor 全修, 含 D8/R1 定性修正——运行面 E 格已 fail-closed 非缺口; 轮2 零新发现; 轮3 分面两路: 面A 零发现, 面B 坑档 1 major(处置④过度概括)采纳修复; 轮4 服务端配额忙, 面B 复核按评审 skill §8 降级主会话自查——零新发现); ship 闸门 vNu 拦出计划 §3.1 一处未闭合 code 标签已修; MSYS 路径转换坑面第三张脸(参数中段 `/xxx`, grep 模式静默零命中)扩进 msys-container-path.md 复发 2

### R1 · 实施收尾 (2026-11-11)

- 2026-11-11 08:37 S1-S6a 五批落地(本地分支 relocate-bt-backup-scalar-probe): 批1 c4ee6149(S1+S2 配置面标量化 + v7→v8 迁移链) → 批2 08b34b54(S3 探测后端纯函数) → 批3 61363210(S4 探测端点) → 批4 2e6487e1(S4 编辑器重写) → 批5 130ec909(S5 运行面口径收尾) → S6a 基线切片 f09830e6 → S6b 真机切片 4281189f。
- 2026-11-11 08:37 分批评审 trailer 摘要(全批入池 0, 复评零 actionable): 批1 config+升级链 816 行 blocker 1 修 1(rm04 旧形状残留); 批2 探测后端 1240 行 blocker 0 修 4; 批3 探测端点 271 行 blocker 0 修 1; 批4 编辑器重写 745 行 blocker 1 修 2(hash 命中候选优先回填); 批5 运行面口径 51 行零发现; 真机切片 106 行 blocker 0 修 4。
- 2026-11-11 08:37 S6a 全量基线(切片 26-11-11-0756): `6000 passed / 2 skipped / coverage 99%`(test.full 实测, HEAD 130ec909)。
- 2026-11-11 08:37 S6b 真机验收(切片 26-11-11-0804): 探测面后端 verdict=hit + hash 消歧唯一命中便携候选 PASS, 编辑器渲染/证据区 PASS, ambiguous 拒回填(D5)真机取证; UI 回填段(hit 回填 → PUT 落盘)与 offline 组被 clone3 s0 大库轮撞场 BLOCKED —— 真机结论 = 部分完成、复测排期(复测清单见切片 §04); 产品缺陷 0。
- 2026-11-11 08:37 S7 收尾回写(本批): pitfalls/backend/qb-fastresume-edit.md 补键形状 v8 口径行; docs/configuration.md「整组迁移」节「顶层 bt_backup 键」改 relocate.bt_backup 标量口径; architecture 主题文档核认 = hr-groups.md「整组迁移」节未承载 fastresume 收尾键形状口径, 无既有落点, 不强造新档; 根 README 核对零 bt_backup 描述未动; 计划文档不动(真机复测未完不翻 Done)。

- 2026-11-11 23:21 S1-S7 实施收尾: 批1-批7 落地(c4ee6149→55aac9cd), test.full 6000 passed/99%, 真机后半 BLOCKED 入池 26-11-11-2305 待排期, 接缝终审零发现

### R2 · 真机复测闭环 (2026-11-12)

- 2026-11-12 02:40 S6 复测闭环: 四判据①②③④全 PASS(切片 `testing/real-baselines/26-11-12-0229-real-relocate-bt-backup-retest.md`, 基线 703ceb6c) —— ① hit 回填→PUT 200→落盘 v8 folded scalar; ② offline 网络层 PASS(manual-set + online=false 未自证标注; offline 渲染形态 UI 不可达为产品面发现, 只记录); ③ 整组迁移四断言面全过(用户拍板 C盘机同盘近似拓扑替代 RM04-21 钉死 R:/D:, 形态差异四条见切片 §04); ④ 清场五步(guard 复跑判红=实例 down 预期形态, 如实记录)。issue 26-11-11-2305 翻 Done; 计划外五条入池裁决留主会话; 坑档两件(cmd_guard skip_tags / dev.webui 重生成配置)入库。
