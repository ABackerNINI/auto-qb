# 26-11-18-memory-bank-index-truncation — 修复 issue 26-11-18-0326: kb.index 行内截断退役, 触发行全量进索引

**Status:** Done
**Added:** 2026-11-18
**Updated:** 2026-11-18
**Summary:** kb.index 生成索引曾按 (摘要 140, 触发 120) 静默行内截断, 全库 120 个坑档触发行全部超限、尾部关键词系统性路由不到; 修法 = 退役行内截断, 摘要/触发词全量进索引, 体积由分卷 cap 单点吸收 (实测 ~109K→~156K 字符, 各卷仍 ≤8000)。附: doc-forms 约定回写、暴露的触发行裸命令手抄改 task id、新增全量可达守卫。
**Topics:** memory-bank-index-truncation

**Refs:** memory-bank/issues/26-11-18-0326-bug-kb-index-trigger-truncation.html

## 本篇只回答

「kb.index 生成索引为什么曾按 (140, 120) 截断、为什么退役、退役的代价与守卫」这一个问题; 分卷机制自身的口径在 conventions/doc-forms.md「索引与检索」。

## 原始请求

1. 用户: 「修复 memory-bank/issues/26-11-18-0326-bug-kb-index-trigger-truncation.html」。
2. 授权确认 (AskUserQuestion): 用户选「授权读+改」—— 允许读改 memory-bank skill 的 kb.index 生成器脚本 (skill 代码禁读例外), 按 issue §06 建议①治本直接修复。

## 思考过程与决策

- **根因定位**: 截断单点 = `gen_kb_index.py` 的 `SUMMARY_MAX=140` / `TRIGGER_MAX=120` + `_clip()` 静默截断; issue 实测的「整行约 239 字符」即触发列 120 截断在整行上的体现。
- **取向判据** (issue §06 要求认领时定夺): 截断是**有意设计** (2026-10-11 单文件时代元数据顶爆 cap), 但 2026-11-05 B4 分卷机制落地后已冗余; 复验实测全库 370 个坑档中 120 个触发行**全部**超限 —— 「截断+可见警告」路线的告警对存量是每轮 120 条的恒久噪音, 「请精简」不可行。故走建议①的「全量保留」支: 退役行内截断, 体积约束回归分卷 cap 单点 (`INDEX_BUDGET=8000`), 没有内容被丢, 连告警机器都不需要。
- **中途改道一次**: 最初实现为「保留截断 + 可见警告 + 截断点收敛到分隔符」; 跑出 121 行告警且发现 `commands run kb.index` 引擎吞 stderr 后, 按上述判据推翻, 改为整体退役 (无上限则 new_doc 提示也一并撤销)。
- **附带修复 (由本批直接暴露, 非顺手改)**: 全量触发行进索引后, 命令漂移检查暴露 `pitfalls/testing/sandbox-venv-in-workspace.md` 触发行手抄裸命令 `uv sync --reinstall` (以前恰好被 120 字符截断遮在索引外) —— 触发行关键词改 task id `env.sync`, 正文未动 (正文本来就用 task id)。

## 实现计划

1. 生成器: 删 `SUMMARY_MAX`/`TRIGGER_MAX`/`_clip`/告警机器, 行内全量渲染; 退役决策与实测代价写进注释 (WARN: 别条件反射加回截断)。
2. 约定: doc-forms.md「索引与检索」明示「触发行全量进索引, 不存在暗预算」。
3. issue: 复验/根因/修复后补充三段落正文, kb.status 翻 Done。
4. 守卫: 新增 `test_kb_index_triggers_fully_indexed` (触发词全文逐字在生成索引页, 防截断回归)。
5. 收尾: 分批评审 + kb.wrap + 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 生成器退役行内截断 + kb.index 重生成 31 件 | Done(2026-11-18) |
| 2 | doc-forms.md 约定回写 + issue 翻 Done 带修法 | Done(2026-11-18) |
| 3 | 全量可达守卫 test_kb_index_triggers_fully_indexed | Done(2026-11-18) |
| 4 | 分批评审 (轮1 4 发现全修 + 复评轮) | Done(2026-11-18) |

## 进度日志

### R0 · 立档 (2026-11-18)

用户指令修复 issue 26-11-18-0326; 授权读改生成器后按上述计划执行; 复验锚点复现 (platform-fs 触发列止于「批处理, .…」), 量化全库 120/370 触发行超限; 修复+评审轮1 (4 发现: 卷数/体积/计数三处数字修正 + 补守卫) 全部采纳, test.quick 全绿(见 kb.baseline)。

- 2026-11-18 04:36 退役 kb.index 行内截断: 触发行全量进索引(全库 120/370 曾超限), 体积回归分卷 cap 单点(~109K→~156K 字符); doc-forms 约定回写 + issue 0326 翻 Done 带修法; 新增全量可达守卫(主题行+类表两路)
- 2026-11-18 04:50 收口: 分批评审 3 轮闭环(轮1 4 发现 + 轮2 1 发现全部采纳修复, 轮3 零发现且历史 5 条确认未回退 —— 裁决后零 actionable; 检 5/5 · 修 5 · 入池 0); 单批任务无跨批接缝, 接缝终审无对象; test.full 全绿(见 kb.baseline), 基线切片 26-11-18-0436 落盘
