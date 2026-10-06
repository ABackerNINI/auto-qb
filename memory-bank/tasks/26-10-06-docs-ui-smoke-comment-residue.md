# 26-10-06-docs-ui-smoke-comment-residue — 注释残留: 改指已退役 ui_smoke.cjs 的 8 处

**Status:** Done
**Added:** 2026-10-06
**Updated:** 2026-10-06 19:17
**Topics:** playwright-e2e
**Summary:** 认领并修 issue 26-10-06-1717(docs 类)。`scripts/ui_smoke.cjs` 随 plan 26-10-06-0708 S7 退役后, **受版本控制**的文件里仍有 8 处**注释**指向它(`app.js:241` / `polling.js:113` + `scripts/ui_harness.py` 6 处), 全部改指 e2e 轨(对应 spec 文件 + `E2E_*` 模式 env)。纯注释改动零行为: 复验 `git grep ui_smoke -- ':!memory-bank'` = **0**, `test.full` **2678 passed + 4 skipped / 99%**(相对上一轮 1840 基线: 覆盖率四项逐位相同, passed +1 全来自并行会话入库的 `9e0b35fc`)。
**Refs:** memory-bank/issues/26-10-06-1717-docs-docs-ui-smoke-comment-residue.html, memory-bank/activeContext/26-10-06-0508-playwright-e2e.md, memory-bank/testing/baselines/26-10-06-1902-docs-ui-smoke-comment-residue.md, memory-bank/pitfalls/docs/drift.md

## 原始请求

> 认领并修复: memory-bank/issues/26-10-06-1717-docs-docs-ui-smoke-comment-residue.html

issue 本体是 S7a 批验收时的旁观发现: 旧脚本退役了, 但产品 js 与桩脚本的注释还在指路, 而当时计划硬约束禁改产品代码 ⇒ 只能入池。

## 思考过程与决策

- **先复验再动手**(防过期原则第 5 条): 入池记的行号是 17:17 的, 三小时后按 `git grep -n ui_smoke` 重跑 —— `src/auto_qb/webui/static/shared/app.js:241` / `polling.js:113` / `scripts/ui_harness.py` 的 L23/L35/L38/L519/L527/L563 逐处仍在, 与记录一致(行号零漂移)。
- **残留面比 issue 记的更窄也更清楚**: 全仓 `git grep` 分三类 —— ①受版本控制的代码 / 配置 / 脚本: **恰好这 8 处**(issue 记的就是全部); ②`memory-bank/` 的冻结件(档案 / 计划 / 报告 / issues / activeContext 切片 / 一次性基线快照): 多处, **一律不回改**(它们记的是"当时是什么样"); ③`.workbuddy*/`(被 gitignore 的 agent 草稿): 若干, 不属仓库面。
- **改法选「指到活的单点」而不是删除指路**: 三处语义不同, 不能一律抹掉 —— ①`app.js` / `polling.js` 的注释是**实测数字的出处**(3000 种子主线程阻塞、窗口化后单轮 refresh 耗时), 出处改指 `e2e/perf.spec.mjs`(块B 的 A/B 埋点); ②`polling.js` 的轮询分档数字另有断言落点 `e2e/views.spec.mjs`「轮询间隔按种子量分档」, 顺手补上; ③`ui_harness.py` 的 6 处是**桩参数与断言组的配套说明**, 而模式矩阵在 S0 已 env 化 ⇒ 改指 `E2E_SKIP_CHECK` / `E2E_HR_SCENE` 与对应 spec(`menus.spec.mjs` / `hr-history.spec.mjs`)。
- **`ui_harness.py` 的「用法」段要交代去向**: 原第二行是「另开终端跑旧脚本」, 现在断言侧由 e2e 轨自动起桩(8137)+ `E2E_*` env 决定形态, 所以改写为「断言已迁 e2e 轨(`commands run dev.e2e`)」+ 一句「手看页面直接开 `http://127.0.0.1:8099/prism/`」—— 保住了这个桩服务自身的手工用途, 不与自动化轨混为一谈。
- **不动 `uv run python scripts/ui_harness.py …` 那一行**: 它是本脚本的自述用法, 也是 `dev.harness` 的定义处镜像; 仓库对 `scripts/` 的命令漂移**逐目录豁免**(理由: 机检脚本自身), 属既有口径, 与本 issue 无关(范围守恒)。
- **不沉守阵**(判据写在这里, 免得下次重新论证): 泛化"退役件零残留"需要一份**退役名册**(哪些名字算退役、谁维护), 首次发生不值这个成本; 真正的教训是**验收 grep 的口径盲区**(S7 的验收只扫 `--include="*.md"` + `memory-bank/` ⇒ 产品 js / py 的注释根本不在面内, 判绿是假绿), 已按"非显然陷阱"写进 `pitfalls/docs/drift.md`。同一坑复发再考虑升格。
  **同一次判断也适用于「不收命令」**: 复验 grep 本会话跑了 3 次、形态也易错(漏掉 `':!memory-bank'` 就把冻结件算成残留), 满足收录判据 —— 但它是**退役动作的一次性验收**, 不属常规工作流, 且其**错形态本身就是判据**(同 `pitfalls/testing/tmpdir.md` 的豁免理由: 把命令换掉这条陷阱就读不懂了)。故留在坑档的「处置」里, 不进 `.commands/`(进去了反而会让坑档那两行被判成手抄副本)。
- **`d2dc3ba1` 在本 clone 不存在**(`git show` 报 unknown revision): 它是迁移分支 `playwright-e2e-migration` 上的原始 hash, 合入 develop 时重写 —— 本 clone 的 S7a 是 `68f6e033`。已在 issue 的完成留痕里补一句, 免得后来者照着旧 hash 查不到。

## 实现计划

1. 复验 8 处锚点仍在(行号 + grep 关键词)。
2. 逐处改注释: `app.js` 1 处 / `polling.js` 2 处 / `ui_harness.py` 6 处。
3. 收尾: 档案 + activeContext 切片 + 基线切片 + 坑档 + issue 置 Done(含 `doc-refs` 认领链)+ `kb.index` + `test.full`。

## 子任务状态表

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 1 | 复验锚点 | ✅ 完成 | 8 处全在, 行号零漂移 |
| 2 | `app.js` / `polling.js` 改指出处 | ✅ 完成 | 出处 → `e2e/perf.spec.mjs`; 分档断言 → `e2e/views.spec.mjs` |
| 3 | `ui_harness.py` 6 处(用法段 + 参数 help + 起盘注释) | ✅ 完成 | 改指 `E2E_*` 模式 env 与对应 spec |
| 4 | issue 置 Done + 认领链 | ✅ 完成 | meta `doc-refs` ↔ 本档案 `Refs` 双向 |
| 5 | 收尾(切片 / 基线 / 坑档 / 索引 / 测试) | ✅ 完成 | 数字见进度日志 |

## 进度日志

- **2026-10-06 18:5x** 开工 `commands run my-commit-flow.sync` → `已同步 c31f6351`。复验: `git grep -n ui_smoke` 受版本控制的 8 处仍在, 与 issue 记录逐处一致; 顺带确认残留全部落在 `memory-bank/` 冻结件与 gitignore 草稿之外**没有**第四类。
- **2026-10-06 19:0x** 改完 8 处(8 行 + 1 行新增的轮询分档指针)。复验 `git grep -n ui_smoke -- . ':!memory-bank'` = **0 处**; 语法面 `node --check src/auto_qb/webui/static/shared/app.js` 与 `ast.parse(scripts/ui_harness.py)` 均过。
- **2026-10-06 19:0x** 收尾: 本档案 + activeContext 切片(专题 `playwright-e2e`, 沿用既有切片)+ 基线切片 + 坑档 `pitfalls/docs/drift.md`「验收 grep 口径盲区」+ issue 置 Done; `kb.index` 重建生成物; `test.full` **2678 passed + 4 skipped / 99%**(语句 16021 / 未覆盖 163 / 分支 5472 / partial 143; 基线 26-10-06-1902)。
  - 首跑(`42.67s`)有 **1 failed** = `test_claim_chain_is_bidirectional`: 档案的 `**Refs:**` 先落盘、被引的基线切片后落盘, 那次全量正好夹在中间(报 "引用的目标不存在")。切片落盘后复跑全绿(48.53s) —— **写序自伤, 不是缺陷**; 顺带实证了认领链守卫对"文件不存在"的即时性。
  - 相对上一轮 1840 基线(2677 + 4 / 16021 / 163 / 5472 / 143): 覆盖率**四项逐位相同**, passed **+1** 归因于并行会话已入库的 `9e0b35fc`(新增守阵 `test_frontend_ctx_menu_refit_by_measured_size`, 改的是 `tests/test_web.py`)。
  - `kb.check`: 主键纪律 OK(467 份 / 254 专题)、认领链 OK; 报**切片数债务 72 > 70**(并行会话累积, 本会话不修 —— 按 cap 债务制转告用户另开会话清理)。
