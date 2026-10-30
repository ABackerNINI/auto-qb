# 26-10-30-backend-deadcode-contract-hygiene — 第二次全项目评审 P3 合并池位收口: 死码批量清理与契约卫生

**Status:** Done
**Added:** 2026-10-30
**Updated:** 2026-10-30
**Summary:** 第二次全项目评审(26-10-30-0237)两个 P3 合并池位收口: 死码/死导入/死分支批量清理(A-08/B-02/F2-01/F2-02/T-05/GH-02 + 3 顺手项)与注解/注释/文档契约卫生(A-07/F1-02/T-04), 两 issue 翻 Done, 行为零差, 全量与工具侧全绿(数字见 kb.baseline)
**Topics:** backend-deadcode-contract-hygiene
**Refs:** memory-bank/issues/26-10-30-0620-chore-dead-code-batch-cleanup-2.html, memory-bank/issues/26-10-30-0620-chore-annotation-comment-contract-hygiene.html, memory-bank/testing/baselines/26-10-30-2326-backend-deadcode-contract-hygiene.md

## 原始请求

1. 用户指令「认领并修复」两份 issue: `26-10-30-0620-chore-dead-code-batch-cleanup-2.html`(死码批量清理合并条 1)、`26-10-30-0620-chore-annotation-comment-contract-hygiene.html`(契约卫生合并条 2) —— 均为第二次全项目 code review(26-10-30-0237)的 P3 合并池位, 用户显式指派 = 认领授权。

## 思考过程与决策

- **开工先复验全部锚点**(防过期原则): 评审行号基准 3d957597, 现 HEAD af619efb 已漂移 —— 全部按符号/grep 重新定位, 12 处锚点全部仍复现(A-08 两死绑定 / B-02 两死导入 / F2-01 seen 死变量 / F2-02 三处死码 / T-05 三处 / GH-02 全仓无发送方 / 3 顺手项 / A-07 判据反向 / F1-02 指路落空 / T-04 双漂移)。
- **A-07 判据镜像方向**: 契约语义「只有显式 False 才停」(与 `paths.source_enabled` 的 `is not False` 同族恒等)。修法取 `if enabled is False: return None` —— 真 bool 下与原 `is not True` 等价(调用方 `tool_client.py` 只喂 `source_enabled()` 的严格 bool), 非 bool 真值不再被误判关闭; 不照抄 `is not False` 字面(那是「启用」侧谓词, 门侧谓词取它的补, 同一恒等判据族)。
- **F2-02 只删登记的死码, 不扩面**: 09 的 `rerender` 在 onClick 里有真实调用点(与 05/06 不同), 保留; 09 死 `chips` 只删整帧重建分支里那份(barHtml 构建器才是 chips 真单点, data-f 委托消费的是它)。
- **T-04 进度注追平以计划档状态行为准**: `26-10-16-0541` 封面「Done(S0–S9 已实施)」, S6-S9 名称逐条取自计划 §03 步骤表; S10 真机验收仍待逐项授权, 如实保留。
- **顺手项跟着池位走**: `客户顿`笔误/死导入两项是纯注释与导入卫生, 与死码清理同一行为零差性质, 按 issue §02 点名一并清。
- **删除面守阵预检**: 动手前 grep tests/e2e 确认无静态守阵钉住被删内容(`_dtMergeRows` 骨架守阵钉的是 `_fetchDrawerSource`/`_DT_FETCH`, 不钉 seen; rerender 无守阵引用), 删除不破守阵 —— 实测证实。

## 实现计划

总体思路: 两池位 12 处全部为行为零差纯卫生, 逐条删除/对齐后 JS 语法机检 + 格式化 + 双侧全量测试, 最后 issue 翻 Done + 基线切片。

1. 池位 1(死码): ops_mod 死绑定×2 / discovery 死导入×2 / drawer_store seen×2 行 / drawer_tpl 05·06 死 rerender + 09 死 chips / gtm 三处死导入死变量 / background.js poll-now 死分支 / 顺手 3 项(runtime.py 死导入, rules/base.py 死导入, module.py 笔误)。
2. 池位 2(契约): agent.py 判据镜像 / app.js 段头注改指现行 rowsFn / gtm `__init__` 进度注追平 S0-S9 + 通知描述改零读盘直达口径 / gtm README 开头段同口径。
3. 收尾: node --check 六个 JS → dev.fmt → test.full + test.gtm → 两 issue 翻 Done + 认领链 → 基线切片 → 索引重建。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 全部锚点复验(12 处, 评审 HEAD 3d957597 → 现 af619efb) | Done(2026-10-30) |
| 2 | 池位 1 死码清理 9 文件(6 登记成员 + 3 顺手项) | Done(2026-10-30) |
| 3 | 池位 2 契约卫生 4 文件(A-07/F1-02/T-04 两处) | Done(2026-10-30) |
| 4 | 机检(node --check + dev.fmt)+ 双侧全量(test.full + test.gtm) | Done(2026-10-30) |
| 5 | 两 issue 翻 Done + 认领链双向声明 + 基线切片 + 索引重建 | Done(2026-10-30) |

## 进度日志

### R0 · 立档 (2026-10-30)

- 2026-10-30 两 P3 合并池位收口: 死码批量清理(ops_mod 死绑定×2, discovery/rules/base/runtime 死导入×4, drawer_store seen 死变量, drawer_tpl 05·06 死 rerender + 09 死 chips, gtm 死导入/死变量×3, background.js poll-now 死分支, module.py 笔误)与契约卫生(agent.py enabled 判据镜像对齐, app.js 段头注改指现行 rowsFn, gtm `__init__`+README 进度注与通知描述按实现取齐); 全部行为零差, test.full 与 test.gtm 全绿(数字见 kb.baseline), 两 issue 翻 Done

- 2026-10-30 23:26 第二次全项目评审两 P3 合并池位收口: 死码批量清理(A-08/B-02/F2-01/F2-02/T-05/GH-02+3顺手项)与契约卫生(A-07/F1-02/T-04)共16文件, 行为零差, 双侧全量绿, 两 issue 翻 Done
