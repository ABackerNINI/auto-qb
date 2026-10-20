# 26-10-21-test-dup-code-audit — Phase 3 重复代码审查(测试与横切, 轮 24-25)

**Status:** Done
**Added:** 2026-10-21
**Updated:** 2026-10-21
**Summary:** 用户「实施计划PHASE3」→ R24 tests/ 重复审查(实测 100241 行/130 py, 拆 A-D 四子轮: 共享助手层整读 + jscpd 112 克隆/pylint 13 组提名 + 结构线索) 产出 **25 项(A11/B5/C6/D3)**, 最大族 = 日志捕获器 7 份实现(A) 与「测试计划」docstring 漂移 **56 文件/约 290 条未列 + 4 文件无清单**(C, ast 机械检查); R25 跨层「同一事实」总账按六主题面合账(配置键面/枚举状态词/颜色令牌/模块契约/中文文案/口径单点), 全局累计 **347 项(A140/B35/C94/D78)**; 入池 **6 条 issue(5 refactor + 1 test, 族级合并)**。纯审查零源码改动, 取证基线 `cecbe4a9`。主线剩 Phase 4(轮 26 汇总)。
**Topics:** test-dup-code-audit
**Refs:** memory-bank/reports/26-10-11-0033-report-dup-code-audit.html,memory-bank/issues/26-10-21-0502-test-test-plan-docstring-guard.html,memory-bank/issues/26-10-21-0502-refactor-test-log-capture-dup.html,memory-bank/issues/26-10-21-0502-refactor-test-shared-micro-helper-dup.html,memory-bank/issues/26-10-21-0502-refactor-test-web-env-param-dup.html,memory-bank/issues/26-10-21-0502-refactor-test-manager-builder-params-dup.html,memory-bank/issues/26-10-21-0502-refactor-test-hr-row-key-surface-dup.html

## 原始请求

1. 用户: 「实施计划PHASE3:26-10-10-2333-plan-dup-code-audit.html」—— 执行该计划的 Phase 3 = 轮 24(`tests/`: Fake/桩/夹具 helpers·webui_helpers·hr_helpers·sidefx 的重复; 断言样板; 「## 测试计划」docstring 与用例漂移) + 轮 25(跨层「同一事实」总账: 配置键面 · 颜色令牌 · 模块契约 · 枚举/状态词 · 中文文案 · 口径单点)。
2. 计划既定口径(拍板冻结): 纯审查不改码; 每轮 S1-S6; 单轮上限源码 ≤4000 行/提名组 ≤30; 可动项按 create-issue 入池(§05 S5/§06 可动项池); 滚动报告逐轮追加并抬 doc-updated。

## 思考过程与决策

- **沿用 Phase 2 先例**: Phase 3 两轮合并单会话收口; R24 按计划 §07 上限拆 **4 个子轮**(R24-A 共享助手层 / R24-B 跨文件内联桩族 / R24-C 断言样板 / R24-D docstring 漂移)。
- **规模实测**: `tests/` = 100241 行 / 130 py(立法基线时 63956/108, 增长 57%); 共享助手层 = conftest 254 + helpers 1200 + hr_helpers 286 + sidefx 465 + webui_helpers 488 ≈ 2693 行, 全量整读(该层是本轮靶心)。
- **机器提名**: jscpd(python, 8/60) **112 克隆/1305 行(1.30%)** + pylint R0801 **13 组**; 关键对照 —— Phase 1 在 src/ 上 jscpd 为 **0 克隆**, tests/ 1.30% = 全仓 Python 字面重复密度最高的面。
- **R24-D 用 ast 机械检查**(stdin 喂 python, 零仓库落盘): 测试计划清单 ↔ `def test_*` 全量比对。
- **B 类沿用 Phase 1/2 口径不入池**(wait_until/假时钟/pointer 写手/env 构建器/hr service 构造器 —— 先钉参数差异); A/C 按**族级合并**入池 6 条(Phase 1 逐轮 46 条 / Phase 2 族级 17 条 / 本轮族级 6 条)。
- **test.full 未跑**: 零源码改动无回归面, 沿 Phase 1/2 纯审查轮先例(基线切片仅随修复轮立)。
- **验收口径**: `git status` 零源码变更(仅 memory-bank/ 制品) —— 见进度日志 R0 的核验行。

## 实现计划

计划 `memory-bank/plans/26-10-10-2333-plan-dup-code-audit.html` §05 六步 × 2 轮 + §06 归档: S1 圈定 → S2 机器提名 → S3 精读(只读) → S4 四分类判定 → S5 归档(报告+入池+档案) → S6 止损; R25 = 各轮 C 类合账 + 跨层对账实证(STATE_RANK / REANNOUNCE / ETA 哨兵在 cecbe4a9 复核)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步 cecbe4a9(快进 546ad848→cecbe4a9) + kb.active + 计划/档案/报告对齐 | Done(2026-10-21) |
| R24-S1/S2 | 圈定 130 py + 机器提名 jscpd 112 克隆/pylint 13 组/结构线索 grep | Done(2026-10-21) |
| R24-A | 共享助手层整读(conftest/helpers/hr_helpers/sidefx/webui_helpers) + 6 项判定 | Done(2026-10-21) |
| R24-B | 跨文件内联桩族验证(_fake_file×4/_pin_disk_usage×4/dat 写手/…)+ 13 项判定 | Done(2026-10-21) |
| R24-C | 断言样板(checking 提交组/grouping 归组样板/calls.count 习语)+ 3 项判定 | Done(2026-10-21) |
| R24-D | 「## 测试计划」docstring ast 机械检查(56 漂移/4 无清单/约 290 未列/幽灵 7 处实证)+ 3 项判定 | Done(2026-10-21) |
| R25 | 跨层「同一事实」六主题面总账 + 跨层常量现状复核(cecbe4a9) | Done(2026-10-21) |
| S5 | 报告 §31/§32 + 覆盖表/变更记录/doc-updated + 入池 6 条 + kb.index | Done(2026-10-21) |
| S6 | 止损核验: git status 仅 memory-bank/; B 类 5 项暂缓未扩池 | Done(2026-10-21) |

## 进度日志

### R0 · 立档与执行 (2026-10-21)

- Phase 3 单会话收口: R24(25 项: A11/B5/C6/D3) + R25(六主题面总账, 全局累计 347 项)。最大发现: ①日志捕获器 7 份实现(helpers/webui_helpers/hr_service/hr_worker/modules_p6/speed_curve/traffic_sample, jscpd 三方逐字坐实); ②「## 测试计划」docstring 与用例双表示漂移 56 文件(AGENTS.md 硬规则无机械守阵, 真残留幽灵 ≥7 处实证); ③tests 字面克隆密度 1.30%(src 为 0) —— tests 是唯一「机器提名即结论」占比较高的审查面; ④C 类重复的根因多为「单点参数面不够」(make_manager/web_env 不可参数化 → 60+15 处旁路), 收敛动作 = 扩参数而非新建。
- 入池 6 条(`type=test` ×1 + `refactor` ×5, 族级合并, topic=dup-code-audit): test-plan-docstring-guard / test-log-capture-dup / test-shared-micro-helper-dup / test-web-env-param-dup / test-manager-builder-params-dup / test-hr-row-key-surface-dup。
- 零改动核验: `git status --porcelain` 仅 `memory-bank/` 路径, `src/`/`tests/`/`scripts/` 为空; B 类 5 项(wait_until ×3、假时钟 ×3、_write_pointer ×3、relocate env ×4、hr service 构造 ×4)按口径暂缓未入池。
