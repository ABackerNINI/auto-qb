# 26-11-11-docs-ship-gate-prerun — 提交闸门预跑 ship.gate

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** 提交闸门预跑 ship.gate: 提交闸门拎成可单独跑的 ship.gate, 接进评审批次 pack 前置, 让小失误在 review 之前暴露
**Topics:** docs-ship-gate-prerun

## 本篇只回答

ship.gate 闸门预跑怎么落地、怎么接进评审流程、行为边界(树净/红线/when_message/双跑)是什么 —— 口径单点在 gate.py docstring 与 pipeline.md「闸门预跑」节, 本篇记决策与进展。

## 原始请求

1. 用户: 「当前一下小失误仅在提交前一刻被闸门拦下, 问题暴露太晚, 比如 小失误 -> review -> 提交 -> 拦下 -> 修改 -> review -> 提交, 初步拟定将提交闸门单独拎出来, 可单独跑, 在合适的时候跑一次, 可能需要修改AGENTS.md/相关skill/命令等等, grilling」
2. 用户: 「按推荐」(11 问 grilling 全部按推荐拍板)
3. 用户: 「按推荐, 出计划再开工」(授权开工: 新建 gate.py/test_gate.py/计划, 改 ship/config.toml 等; commit/push 等显式「提交」)

## 思考过程与决策

- 设计树经 11 问 grilling 全部拍死, 计划档案: [26-11-11-0408-plan-ship-gate-prerun.html](../plans/26-11-11-0408-plan-ship-gate-prerun.html)(D1-D11 拍板表)。核心: 预跑照搬全部 auto 闸门(清单单点不改); 时点 = code-review skill ③ pack 前置(sync 之后、pack 之前, dev.fmt 真动作必须先于 pack); commit 双跑保留不缓存(D3); AGENTS.md 一字不动(D8); 凡 pack 必前置(D9)。
- 收益锚定: 评审基哈希排除生成物/记账类 → 重评浪费只在闸门逼改可评内容时发生; 预跑目标 = review 评到的树已是闸门绿。
- 实现复用: 闸门引擎早已在 _pipeline.py(gates_for/run_gates), gate.py 只是新入口(147 行); 新闸门级键 when_message(消息依赖闸门, 预跑侧无消息文件时略过; commit 侧免疫 —— commit 在闸门前就因消息缺失拒跑)。

## 实现计划

按计划 §04 六步: gate.py 入口 → 三处配置注册(GATE_KEYS/toml/ship config) → skill 接线 → 测试 → dogfood → 回写收尾。每步验收判据见计划 §04 表。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | gate.py 入口(快照/argv/safety/树净/红线 WARN/when_message 过滤/全量明细/成功一行) | Done(26-11-11) |
| 2 | ship/config.toml 注册 + GATE_KEYS 扩键 + review.trace 加 when_message | Done(26-11-11) |
| 3 | code-review SKILL.md ③ pack 前置接线 | Done(26-11-11) |
| 4 | test_gate.py 16 用例(测试计划 docstring 同步) | Done(26-11-11) |
| 5 | dogfood: ship.gate 真跑全绿(引擎注入/输出透传/略过行全验证) | Done(26-11-11) |
| 6 | 回写 pipeline.md + 分批评审(2 分面 + 增量复评, 零 actionable) + 基线切片 + 坑档 2 条 | Done(26-11-11) |
| 7 | 提交(等用户显式「提交」) | Open |

## 进度日志

### R0 · 立档 (2026-11-11)

- grilling 11 拍板 → 计划 HTML → 全量实现 + 两分面评审(6 条 minor 全修) + 增量复评零发现; 包测试 / ASCII 守卫 / 全量测试全绿, 数字见基线切片 [26-11-11-0504](../testing/baselines/26-11-11-0504-ship-gate-prerun.md); ship.gate dogfood 三次全绿(含远端两次推进后的重跑)。坑档 2 条: testing/engine-pack-dir-injection(引擎注入 PACK_DIR 指向 task 所在包), ops/entry-main-missing-silent-noop(入口 __main__ 漏 main() 调用 = [ok] 假绿)。
