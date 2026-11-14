# 26-11-14-test-cmdflow-hardening — my-commit-flow 包测试临时目录锚定加固与跨宿主语义修复 —— T4 移植事故后续

**Status:** In Progress
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** T4 移植事故(探针解析落空 → rmtree(CWD) 删整仓)的根治与纵深: 快照锚定不变量+探针侧信道+conftest 防呆闸+sweep 双防呆, 另修 _pipeline 跨宿主语义归一; 两 issue 已 Done, 残余见 issue 0912 修法 B 记录
**Topics:** test-cmdflow-hardening
**Refs:** memory-bank/issues/26-11-14-0857-bug-my-commit-flow-snapshot-anchor.html,memory-bank/issues/26-11-14-0912-test-pipeline-win-path-asserts-linux-red.html

## 本篇只回答

T4 移植事故(沙箱 shim 干扰令包测试 cleanup 误删整仓)暴露了哪些测试基建缺陷、各自怎么修、验证数字是多少 —— 事故链与机制实证单点在 issue 0857, 本文只记修法决策与推进流水。

## 原始请求

1. 「T4 报告包含一起重大事故: 子智能体跑 my-commit-flow 自带测试时, test_snapshot.py 的 cleanup 逻辑在沙箱 AppImage shim 干扰下把整个仓库(含 .git)递归删除…分析是否有缺陷」(问答轮)
2. 「①+②」= 入池 issue + 直接修 test_snapshot.py
3. 「范围外发现入池, fix the issue 26-11-14-0857」= test_pipeline 两例 Linux 恒索单独入池(0912) + 修复 0857 的 P1/P2 残余
4. 「commit」; 闸门被 0912 挡死时拍板「use subagent to fix the issue, choose 方案 B」

## 思考过程与决策

- **缺陷定案(问答轮实证)**: `Path("")` 语义恒等 `Path(".")`, 两处 `addCleanup(rmtree(snap.parent, ignore_errors=True))` 在探针解析落空时把测试进程 CWD(仓库根)递归删空; 缺陷在源头(本 clone), 移植现场只提供触发条件 —— 详见 issue 0857 §02/§05。
- **P0 修法**: 快照落点不变量(`<gettempdir>/<SNAPSHOT_PREFIX>*/pack`)先验证再许 rmtree, fail 先于 cleanup 注册(结构保证); ProbeAnchorTest 钉守卫。
- **P1a**: stdout 是被 shim 吞改的入口面 ⇒ 探针报告走 COMMAND_FLOW_PROBE_OUT 侧信道文件, stdout 降级兜底; 全部断言面经 `_probe_text` 单点取值(评审 R2 #5)。
- **P1b 改道**: 原建议「拒绝仓库根 CWD 起跑」不予实施 —— test.pkg 以仓库根起跑是设计口径; 只拦「temp 落仓库内」(rc=4, 与 tests/ 自举同口径), 判据与 `_find_repo_root` 同源(HEAD/文件形态)。
- **P2**: sweep 双防呆 = gettempdir 回落 CWD(realpath 口径)整体跳过 + 目标自证含 `pack/scripts/_snapshot.py`。
- **0912 方案选择**: 生产调用面核实(`run_git` 全部调用方传裸 `"git"`), 方案 A(止血)与 B(归一化)摆给用户, 用户拍板 B —— `_subcommand` 反斜杠归一取 stem、`_short` 形态集合正反两向备齐; Windows 侧不变有逐用例推演, 实测回归由 Windows clone 闸门兜底。
- **不新建基线切片**: 本批 tests/ 与 src/ 零改动, 主套件基线仍是事实源; 包内脚本测试数字按 baseline.md「两侧都重测再落数字」警告, 本 clone 只有 Linux 侧, 硬造切片反制造漂移。

## 实现计划

1. P0 锚定守卫(`_snap_from_probe` + ProbeAnchorTest) → 2. 入池 0857 → 3. P1a 侧信道 / P1b conftest 闸 / P2 sweep 双防呆 → 4. test_pipeline 两例恒红入池 0912 → 5. 0912 方案 B(子代理实施, 主会话亲核) → 6. 分面评审循环(派发 3: 正确性+安全 / 测试缺口 / 文档事实; 修复轮至零 actionable) → 7. 收尾回写与提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | P0 锚定守卫 + ProbeAnchorTest(issue 0857 P0) | Done(2026-11-14) |
| 2 | P1a 探针侧信道 + _probe_text 单点(issue 0857 P1a) | Done(2026-11-14) |
| 3 | P1b .commands/conftest.py 防呆闸 + test_conftest_guard.py 回归阵(issue 0857 P1b) | Done(2026-11-14) |
| 4 | P2 _sweep_old 双防呆 + 私有根活用例(issue 0857 P2) | Done(2026-11-14) |
| 5 | 0912 方案 B: _subcommand/_short 归一化 + POSIX 用例(子代理实施) | Done(2026-11-14) |
| 6 | 分面评审循环 3 轮至零 actionable(检 7/7) | Done(2026-11-14) |

## 进度日志

### R0 · 立档 (2026-11-14)

问答轮定缺陷(T4 事故链与源码逐行吻合, 机制实证 Path("")即 Path(".")) → 用户批 ①入池+②修 P0 → 追加批: 0912 入池 + 0857 P1/P2 全修 → 提交批: 闸门被 0912 挡死, 用户拍板方案 B 交子代理实施; 分面评审 3 轮(派发 3)修 7 条至零 actionable。两 issue 均 Done, 实测 test.pkg 499 passed 0 failed(Linux 宿主首次全绿, 见 issue 0912 修复后补充)。

- 2026-11-14 10:32 T4 事故后续: 0857 P0-P2 全修+0912 方案B(子代理), 分面评审3轮检7/7修7零actionable, test.pkg 499 全绿, 两 issue Done 随本批入库
