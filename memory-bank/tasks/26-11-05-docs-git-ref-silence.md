# 26-11-05-docs-git-ref-silence — git ref 自愈静默与排障开关

**Status:** Done
**Added:** 2026-11-05
**Updated:** 2026-11-05
**Summary:** ref 自愈成功/自愈失败均静默放行(失败说明行仅 COMMAND_FLOW_DEBUG=1 可见), 正常路径只给 hash 结论; 真不一致仍 [STOP] rc=1; 输出契约 v7
**Topics:** docs-git-ref-silence
**Refs:** memory-bank/testing/baselines/26-11-05-0952-docs-git-ref-silence.md

## 原始请求

1. 「git ref 的问题处理已全权交由脚本不出错的情况下应该不用提醒」(示例为 `packed-refs 陈旧已自动修复…——提交已落稳` 那行噪音): 成功自愈不提醒, 只有失败 / 无法核实 / ref 不一致才必须报。
2. 追加:「`packed-refs 自动修复未生效` 降级到仅排障模式」——默认不出现, 只在 debug/verbose 或专用排障输出可见; 硬失败仍报且 rc=1。
3. 追加:「只要不出错就不需要 agent 去关心 ref 的问题，ref 与 hash 不同」——脚本成功时对外只给 commit hash 结论, agent 不主动提 ref。
4. 用户确认执行: `test.full` + DoD 收尾回写 + 提交推送。

## 思考过程与决策

- 提示来源定位: 噪音行由 [verify_ref.py](../../.commands/my-commit-flow/scripts/verify_ref.py) 的 `_autoheal_packed_stale` 成功分支返回, `ship.commit` 与 `verify-ref` 原样打印 —— 改脚本输出行为, 不是改汇报模板。
- 三分支定调: ①成功自愈 → 静默(结论由 `ref 一致 <hash>` / `提交成功 <hash>` 承担); ②自愈失败但三处真值一致 → 放行且默认静默, 说明行仅 `COMMAND_FLOW_DEBUG=1` 可见; ③分支 ref 真不一致 / 无法核实 / staged 暴增 → 完整 `[STOP]` 处置步骤, rc=1。
- 排障出口选型: 包内无现成 debug/verbose 机制; 复用 `COMMAND_FLOW_*` 环境变量族新增 `COMMAND_FLOW_DEBUG`, 严格只认 `=1`; **不新增 `.my-commit-flow.toml` 配置键**, 不触碰 `src` 的 `validate_config`。
- 「ref 与 hash 不同」的口径: ref 是内部记账(分支指针 / packed-refs 缓存), hash 才是交付事实; 脚本核对通过后 ref 记账差异不构成异常, agent 汇报不主动提 ref。
- 输出契约版本: v5 → v7(v6 只出现在中间文案、未落盘定义, 统一收敛为 v7, 避免版本号不自洽)。
- 收口评审: 全能档(diff 81 行, 1 只读子代理), 3 发现(2 minor + 1 nit), 引文 3/3 过 `review.check`; 当场修 3(minor: 严格 DEBUG=1 / 默认静默用例先清宿主环境; nit: v6/v7 统一为 v7), 入池 0。

## 实现计划

1. 定位提示语产生位置(脚本 vs 汇报模板)并读 git pitfalls 路由。
2. `verify_ref.py`: 成功自愈返回空; 自愈失败说明行加 `COMMAND_FLOW_DEBUG=1` 门控; 契约升 v7。
3. 同步 `commit.py` 两处打印点注释、`test_commit.py` 断言、`references/pipeline.md` 与 `pitfalls/git/refs.md` 口径。
4. 验证: 包单测 + `%TEMP%` 临时仓库实测成功 / 自愈失败(默认+DEBUG) / 真不一致三路径。
5. 收口评审 → 全量测试与基线切片 → 收尾回写 → 提交推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 定位提示来源 + git 路由/坑档阅读 | Done(2026-11-05) |
| 2 | verify_ref 成功静默 + DEBUG 门控 + 契约 v7 | Done(2026-11-05) |
| 3 | 测试与文档口径同步 | Done(2026-11-05) |
| 4 | 包单测 + 临时仓库三路径实测 | Done(2026-11-05) |
| 5 | 收口评审(全能档) + 全量 + 基线 + 收尾提交 | Done(2026-11-05) |

## 进度日志

### R0 · 立档 (2026-11-05)

- 定位: 噪音行来自 `verify_ref.py` 的 `_autoheal_packed_stale` 成功分支, 由 `ship.commit` / `verify-ref` 打印; 非汇报模板。
- 实现: 成功自愈返回空信息行; 自愈失败说明行仅 `COMMAND_FLOW_DEBUG=1` 时返回; 真不一致路径不变(`[STOP]` + rc=1); 输出契约 v5 → v7。
- 口径回写: `references/pipeline.md`(成功静默/失败降级 + 只给 hash 结论) 与 `pitfalls/git/refs.md`(对外口径 + 排障命令) 已同步。
- 实测: 包单测绿 + 临时仓库三路径(成功静默 / 自愈失败默认静默且 DEBUG=1 可见 / 真不一致 rc=1)全过; 全量与覆盖率见 kb.baseline。
- review: blocker 清零, 修 3(minor 2 + nit 1, 均引文过 `review.check` 后当场修), 入池 0; 档位 = 全能(81 行, 1 只读子代理)。
- 本轮改动随本专题入库: verify_ref.py / commit.py / test_commit.py / pipeline.md / refs.md。

- 2026-11-05 09:45 ref 自愈成功/自愈失败均静默放行(失败说明行仅 COMMAND_FLOW_DEBUG=1 可见), 真不一致仍 [STOP] rc=1; 契约 v7 + 收口评审 0 blocker
