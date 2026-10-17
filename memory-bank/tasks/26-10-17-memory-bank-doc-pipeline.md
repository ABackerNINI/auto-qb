# 26-10-17-memory-bank-doc-pipeline — memory-bank 文档流水线: 建件与收尾命令化 (P1-P3)

**Status:** Done
**Added:** 2026-10-17
**Updated:** 2026-10-17
**Summary:** 建件与收尾全命令化: kb.new 按族注册表派生建件(一次逻辑动作=一条命令+一次填空), kb.status/kb.bump/kb.wrap 收录改版与收尾机械面; 文档回写四处(doc-forms/AGENTS.md/README/SKILL.md); P1-P3 全绿验收(test.full 全绿, kb.check/doc.drift/doc.caps 全绿 —— 数字见 P3 基线切片)
**Topics:** memory-bank-doc-pipeline
**Refs:** memory-bank/plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html

## 原始请求

1. 实施计划 `memory-bank/plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html` 的分阶段交付(P1 时戳/时间单点 · P2 状态/改版收录 · P3 二期四族与文档回写)
2. 中途指令「修复缺陷, 然后只提交本地」(P1 两潜伏缺陷修复 + 本地提交, 远端未推)
3. 收尾指令「建档」: 立本专题任务档案(§08 立档注记的显式确认)

## 思考过程与决策

- 设计轴: **一次逻辑动作 = 一条命令 + 一次填空** —— 命令是既有单点(时间戳/状态词表/命名/索引)的执行器, 不造第二套规范
- 族注册表 `_common.FAMILIES` 单点: 命名/模板/词表/索引动作定义一次, kb.new 与守卫同源
- 头部零 SLOT 契约: 机器字段命令派生; 触发词是路由判断不可派生 → 走 `--triggers` 参数(裁定 A7)
- 基线 `--total` 由 test.full 实测誊写(裁定 A4 —— 命令不编造数字); `--title` 预填 Summary(A1)
- kb.wrap 只做机械面(D6): 蒸馏与判断仍是 agent 的活
- 冻结线 26-10-17-0736: 之后新建族文件入守卫检查面; 坑档/进展无时间戳不可判新旧, 跳过(既有守卫兜底)
- 可引述豁免: 代码跨度与围栏块不扫 SLOT(与 check_wording 口径对齐, 修基线误报)
- 切片统一由 kb.wrap 收尾处理(slice 族不走 kb.new)
- 计划路径: memory-bank/plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html(D1-D6 裁定已并入)

## 实现计划

1. P1 时戳/时间单点(timekit 派生 + 冻结线守卫) —— Done(2026-10-17)
2. P2 状态/改版收录(kb.status/kb.bump + D4 双向认领) —— Done(2026-10-17)
3. P1 两潜伏缺陷修复(match_domain 最长前缀匹配 + 基线计数笔误勘误) —— Done(2026-10-17)
4. P3 二期四族模板(pitfall/report/baseline/progress + 注册表扩展) —— Done(2026-10-17)
5. P3 kb.new 参数化分发 + 守卫扩面 + 测试补强 —— Done(2026-10-17)
6. P3 文档回写(doc-forms/AGENTS.md/README/SKILL.md) —— Done(2026-10-17)
7. 验收收尾(test.full 基线 · kb.check/doc.drift/doc.caps · kb.wrap · 立档) —— Done(2026-10-17)

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | P1 时戳/时间单点 | Done(2026-10-17) |
| 2 | P2 状态/改版收录 + D4 | Done(2026-10-17) |
| 3 | P1 缺陷修复(领域解析/勘误) | Done(2026-10-17) |
| 4 | P3 四族模板 | Done(2026-10-17) |
| 5 | P3 命令/守卫/测试 | Done(2026-10-17) |
| 6 | P3 文档回写 | Done(2026-10-17) |
| 7 | 验收收尾与立档 | Done(2026-10-17) |

## 进度日志

### R0 · 立档 (2026-10-17)

P1-P3 全部实施验收完成: 四族模板 × 注册表扩展 × 守卫扩面(检查面 4 件全绿) × 命令参数化 × 四处文档回写; test.full 全绿(数字誊写进 P3 基线切片, 见 kb.baseline, 不写正文), 狗粮自验 kb.status/kb.bump/kb.new baseline/wrap 全跑通。计划已翻 Done; 本档案随切片 R7 收尾落盘。

- 2026-10-17 10:06 立档: 任务档案 memory-bank/tasks/26-10-17-memory-bank-doc-pipeline.md 落盘(§08 显式确认), R0 进度日志 + D4 反向认领进计划; 档案 kb.status 翻 Done

- 2026-10-17 10:16 提交合入推送: 用户触发「合入 develop 正常推送」⇒ ship.commit --no-push 落 P3 提交(87515aa4, 闸门全过) → develop 快进远端 f32f37a4 → feature rebase 上线(P1/P2/P3 三笔重放, tasks/_index.md 生成物冲突机械再生解) → develop 快进合入 → ship.push 推送成功 4f11be5c(死锁解除: 无远端对应分支的问题改走 develop 主线)

- 2026-10-17 10:29 模板 .sheet 边距调宽(880→1120px, 侧 padding 40→20px)两模板同改, 内容区 1080px 让给表格/pre; 临时模拟建档(kb.new plan, 10 SLOT)+守卫+前后截图验收通过; test.full 3502+4 与上基线逐位一致; 规格回写 webui.md, 新基线切片 26-10-17-1028-tpl-sheet-margin

- 2026-10-17 10:37 模板版面改自适应: sheet 1280 封顶 + clamp 侧距, 移除 prose ch 上限使正文/列表/表格/代码块同宽; 新增 <=1180px 断行规则防窄视口横向溢出; playwright 三档视口实测右缘逐位一致; 模拟建档+守卫+截图验收通过; 规格回写 webui.md, 新基线切片 26-10-17-1036-tpl-adaptive-sheet

- 2026-10-17 11:37 修 GitHub CI 偶发红 test_new_doc_refuses_slice_and_duplicates (本计划 P2 交付用例): plan 族文件名带分钟级戳 (`%y-%m-%d-%H%M`), 真墙钟两次调用跨分钟则文件名不同、幂等拒绝永不触发 —— 机制级红验复现 (相邻分钟各建一件、第二次不拒绝), 定性为用例时刻竞态、非产品缺陷; 用例冻结 timekit.now 钉同分钟 (同族先例 pitfalls/testing/flaky-midnight-daycount.md)。全量复绿, 实测数字见 kb.baseline。
