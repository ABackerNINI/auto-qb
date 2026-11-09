# 26-11-10-backend-relocate-relpath-finalize — fastresume 相对键 profile base 解析改写(同盘部署收尾链修复)

**Status:** In Progress
**Added:** 2026-11-10
**Updated:** 2026-11-10
**Summary:** 认领并修复 issue 26-11-07-2336: qB 便携部署同盘符时 fastresume 三路径键写 basePath 相对形态, 改写器只认绝对形态致收尾链失效 —— 修法=issue 建议①(相对键按 profile base 解析改写), base 由 bt_backup 上两级单点推导(qB 源码实证), 解析不命中保守跳过; 建议②(预检告知)失去前提不做
**Topics:** backend-relocate-relpath-finalize
**Refs:** memory-bank/issues/26-11-07-2336-bug-relocate-same-drive-finalize.html

## 本篇只回答

issue 26-11-07-2336(同盘部署收尾链无效)怎么修的: qB 相对形态键的机制依据是什么、base 从哪推导、改写判据如何保持保守、真机复验还差什么。

## 原始请求

1. 用户: 「修复memory-bank/issues/26-11-07-2336-bug-relocate-same-drive-finalize.html」

## 思考过程与决策

- **机制实证(上网核 qB 源码)**: `bencoderesumedatastorage.cpp` 三路径键(save_path/qBt-savePath/qBt-downloadPath)统一过 `Profile::toPortablePath`; `profile_p.cpp` Converter: Windows 只对与 basePath 同盘符的绝对路径相对化, `fromPortablePath` = `basePath / rel` 还原; `application.cpp`: portableModeEnabled(portable 目录在场)恒开相对化, 装版(DefaultProfile)不开(NoConvertConverter)。CustomProfile 布局: basePath = `<root>/qBittorrent`, dataLocation = basePath/data, BT_backup = basePath/data/BT_backup ⇒ **basePath = BT_backup 上两级**。与 E2c 实测(环境2, 4 层 dot, `..\..\..\..\Users\...`)互证。
- **决策 1(修法 = issue 建议①)**: 改写器支持相对形态解析改写; **建议②(迁移预检同盘部署 confirm 告知)不做** —— ①修掉本体后同盘部署收尾链恢复有效, 告知失去前提。
- **决策 2(保守性不破)**: base 推导错位只造成「解析不命中旧新根 → 照旧跳过」, 不产生错改写 —— 产物恒为新根绝对形态, 不依赖 base; 解析失败(上弹越根)/不命中 → unmatched 原值保留(N10 纪律的修定而非废除)。
- **决策 3(产物形态)**: 改写产物 = 新根**绝对**形态(跨盘部署 E2 已实证绝对键加载全绿), 分隔符 = base 根分隔符(部署平台语义); qB 侧下次写盘自然重新相对化, 无干扰。
- **决策 4(真机复验延期)**: 本轮纯桩面修复(改写器纯字符串变换可测) + qB 源码机制实证; 真机 E2c 同盘拓扑复验留待下次真机轮(需专项排期, 见子任务表 Open 项)。

## 实现计划

1. fastresume.py: `_split_absolute`(盘符/UNC/POSIX 三根形态) + `_relative_form` + `_resolve_relative`(点段/上弹/越根拒绝) + `profile_base_of`(BT_backup 上两级) + `rewrite_save_paths(..., profile_base="")` 相对键解析进既有前缀管道 + `retarget` 内部接线。
2. recycle_daemon.py: unmatched 记账注释同步(相对键已可改写, unmatched = 解析失败或不命中)。
3. 测试: E2c 形态字节样本(反斜杠/正斜杠相对键/等值与根下命中/产物绝对新根/幂等重放) + 不命中面(指旧新根之外/越根/无 base 旧链兼容) + POSIX 面 + profile_base_of 形态表 + retarget/daemon 两级端到端; 既有 N10 钉(无 base 跳过)保留。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | fastresume.py 相对解析四件 + 管道接线 | Done(2026-11-10) |
| 2 | recycle_daemon.py 注释同步 | Done(2026-11-10) |
| 3 | 测试 6 用例 + daemon 接线用例 | Done(2026-11-10) |
| 4 | 分批评审 + 修复(blocker 2: Linux CI 宿主风味断言) | Done(2026-11-10) |
| 5 | 全量绿 + 基线切片 + issue 翻 Done | Done(2026-11-10) |
| 6 | 真机 E2c 同盘拓扑复验(qB 5.2.3 便携, 非 mover 成员重启到位) | Open(下次真机轮) |

## 进度日志

### R0 · 立档 (2026-11-10)

- 修复实施 + 评审两轮(轮1: blocker 2/nit 2 全修 —— 两条 blocker 是新增 e2e 断言硬编码反斜杠在 Linux CI 必红, 修为按宿主 tmp_path 风味选分隔符; 复评见 R1)。

- 2026-11-10 01:32 认领并修复 issue 26-11-07-2336(已翻 Done): fastresume 相对键按 profile base 解析改写 —— qB 源码实证三键 toPortablePath/basePath=BT_backup 上两级/portable 恒开, 改写器四件新增(_split_absolute/_relative_form/_resolve_relative/profile_base_of)+ retarget 接线, 解析不命中保守跳过(N10 修定不废除), 建议②预检告知失去前提不做; 评审 4 轮(轮1 blocker2+nit2 全修, 轮2-4 零 actionable), 坑档 patching 复发+1; 全量全绿见 kb.baseline, 基线切片 26-11-10-0132; 真机 E2c 同盘拓扑复验留待下次真机轮
