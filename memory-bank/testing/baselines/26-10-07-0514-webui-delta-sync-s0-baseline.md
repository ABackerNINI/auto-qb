# 2705 —— WebUI rid 式增量同步实施计划 S0 基线 (feat/webui-delta-sync @ 644663be, 开工对照点)

> 摘要: 计划 [26-10-07-0414-plan-webui-delta-sync.html](../../plans/26-10-07-0414-plan-webui-delta-sync.html)
> 第 0 步 (S0): 落一条增量同步动工前的全量测试基线, 作为后续 S1-S10 逐段收益对比与回归判据的对照点。
> 本轮 src / tests 零改动, 基线用途 = 记录实施开工前 test.full 真值 + 在账量级口径。
> 基线时间: 2026-10-07 05:14

**Refs:** memory-bank/plans/26-10-07-0414-plan-webui-delta-sync.html, memory-bank/reports/26-10-07-0204-report-webui-delta-sync-feasibility.html

## test.full 实测

- 分支: feat/webui-delta-sync @ 644663be(树净, 无未提交改动; 本地分支, S0 步不做 sync)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2705 passed + 4 skipped, 0 failed, 36.40s, 覆盖率 TOTAL 99%**
  (15863 语句 / 163 未覆盖 / 5496 分支 / 143 partial; 门槛 98% 达标)
- 相对上基线 [26-10-07-0458](26-10-07-0458-kb-nav-issue-type-column.md)
  (2705 passed + 4 skipped @ 36.10s, 16061 语句 / 163 未覆盖 / 5496 分支 / 143 partial):
  passed / skipped / 未覆盖 / 分支 / partial 五项**逐位相同**, 耗时同量级 (+0.30s);
  仅语句总数 16061 → **15863**(-198)。该 ±200 语句漂移为**已在账的复现现象**
  (近期切片在 ~15.8k 与 ~16.0k 两簇间摆动: 15823/15863 vs 16021/16061, 而 passed/分支/partial
  恒定; 先例见 [26-10-06-0144](26-10-06-0144-full-code-review-remediation-s0-baseline.md)
  「15815→15624(-191), 确认非代码变化所致」)。按口径以**本次实测 15863** 为 S0 对照真值。
- 4 skipped 为 Windows 侧 POSIX 专属存量, 与 in 账一致。

## 收益对比 before(量级口径, 在账实测, 非 S0 重测)

后续 S1-S10 各步的收益对比均以此为 before 基准(出处: 可行性报告 26-10-07-0204 §02④):

- **服务端全量回包** (3000 种子, 2026-09-19, P1-1 之前口径, issue 1): 全量回包 **6.3 MiB** /
  json.dumps **26.4ms** —— 组行内嵌完整成员数组(members_view)是 6.3 MiB 主体
  (views.py:494-495; 可行性报告 §08「粒度事实」callout)。
- **一轮「序列化+网络+解析」** (3000 种子): ≈**63ms**(runtime.py:793-794 注释口径 ——
  「绝不推数据」事件驱动只推版本号的依据)。
- **前端 refresh 单轮耗时** (2026-09-19 实测定档, polling.js:111-115 注释): 1000 种子 **143ms** /
  3000 种子 **309ms** / 5000 种子 **396~501ms**; 据此分档轮询间隔 ≤1000→1.5s / 1000~3000→2s /
  >3000→3s(主线程占用 ≈10%/15%/17%)。
- S0 本轮未重测上述量级数字(计划 S0 DoD 只要求记录在账口径); 真机复测在 S10 对照分档实测。

## 对照判据(S1-S10 逐段沿用)

- 每段修完对比 passed / skipped / 未覆盖 / 分支 / partial 五项: 预期只应 passed 不降、
  未覆盖 / partial 不升; 回退先查该段改动。
- 覆盖率 TOTAL 门槛 98%; 语句总数 ±200 内的摆动按上述在账现象解读, 不当回归。
- 量级收益: 增量落地后全量回包 6.3 MiB / 63ms 一轮 / 前端分档 refresh 耗时的下降幅度,
  以 S10 真机分档实测对照本切片「before」段。
