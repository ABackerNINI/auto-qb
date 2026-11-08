# 26-11-08-backend-mypy-typecheck-debt — 清偿 dev.typecheck 后端类型债: 全库 mypy 归零

**Status:** Done
**Added:** 2026-11-08
**Updated:** 2026-11-08
**Summary:** 认领并清偿 issue 26-11-08-0118: 复验现象由八条漂移到十二条, 五文件按同一根因收窄归零, 全量测试全绿(见 kb.baseline)
**Topics:** backend-mypy-typecheck-debt
**Refs:** memory-bank/issues/26-11-08-0118-refactor-mypy-backend-typecheck-debt.html

## 本篇只回答

本档案只回答: 计划外 issue 26-11-08-0118(dev.typecheck 类型债)怎么清偿、复验漂移怎么处置、验收口径是什么。mypy allowlist 机制的领域结论在 pyproject.toml 注释与守阵测试, 不在本篇重复。

## 原始请求

1. 用户原话: 「修复memory-bank/issues/26-11-08-0118-refactor-mypy-backend-typecheck-debt.html」—— 即用户指派认领并修复该 issue。
2. 未授权的动作一律不做: 不 commit/push、不入池新 issue、不改其它 clone。

## 思考过程与决策

- D1 复验先行: issue 按防过期原则第 5 条要求认领时重跑锚点。开工同步快进 112 笔后重跑 dev.typecheck, 原四文件八条逐条仍在, 另多出 hr/model.py 四条同源 union-attr(远端带入的 from_json 形状守卫)。判定「四条新增与原有八条同一根因、同一修法, 且不清零则 dev.typecheck 仍红、issue 无法 Done」, 按 scope-guard 例外 1(阻塞)纳入本批, 在回复与 issue 正文点名范围变化。
- D2 修法只走源码, 不动 allowlist: pyproject [tool.mypy] 的 per-module 豁免由 tests/test_mypy_allowlist_guard.py 冻结(只减不增), 新增豁免当场判红; 且递减是主轴, 为消错加豁免是倒退。
- D3 零运行时行为变化优先: 主要修法是把 `x = d.get(k) if isinstance(d.get(k), dict) else {}` 改成先取局部变量再 isinstance 收窄 —— 两次独立调用让 mypy 无法收窄(类型残留 None), 提取局部变量后收窄生效, 运行时语义逐字等价(少一次纯函数 get)。
- D4 回写判断 = 零回写: 本批没有接口/行为/配置键/数据形状变更, memory-bank 主题文档与根 README 无事实可更新。
- D5 真机验收不适用: 纯类型注解与局部变量重构, 运行时行为不变, 桩与全量测试即可覆盖(理由在此明示, 按收尾 DoD 真机自检口径)。

## 实现计划

1. 开工同步 + 复验 typecheck 取行号, 置 In Progress。
2. 五文件按三类修法改源码, dev.fmt, dev.typecheck 归零。
3. test.full 全绿; 分批评审(全能档只读子代理)。
4. 收尾: issue 留痕翻 Done、立档、切片、基线切片、坑档、kb.index、kb.check。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 同步 / 复验 / 置 In Progress | Done(2026-11-08) |
| 2 | 五文件修法 + typecheck 归零 | Done(2026-11-08) |
| 3 | test.full 全绿 + 分批评审 | Done(2026-11-08) |
| 4 | issue 留痕 / 立档 / 切片 / 基线 / 坑档 / 自查 | Done(2026-11-08) |

## 进度日志

### R0 · 立档 (2026-11-08)

- 认领并修复 issue 26-11-08-0118: 复验现象由八条漂移到十二条(新增 hr/model.py 同源四条), 五文件按同一根因收窄 + 两处字典注解 + 一处参数非空守卫, dev.typecheck 全库零错。
- 全量测试全绿(见 kb.baseline) · dev.typecheck 零错 · 分批评审三轮闭环: 首轮源码零发现, 收尾文档复评 1 条 minor(issue §05 把「八处赋值」误写成「九处」, 引文校验通过后当场修正), 第三轮零 actionable; 累计 review.check 一条过检一条修, 零入池。接缝终审与复评同轮完成(单批收口, 无跨批接缝)。
- 回写判断 = 零回写; 真机不适用(纯类型层面, 运行时行为不变)。新坑 pitfalls/testing/mypy-isinstance-narrow-repeated-get.md。随本专题入库。

- 2026-11-08 18:18 认领并清偿 issue 26-11-08-0118: 复验 8→12 errors, 五文件同一根因收窄 + 字典注解 + form 非空守卫, typecheck 归零, 全量绿, 评审 0 发现
