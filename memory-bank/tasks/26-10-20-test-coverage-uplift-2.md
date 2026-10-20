# 26-10-20-test-coverage-uplift-2 — 覆盖率门槛清偿与 99% 冲刺 · 第二阶段 (97.7% → 99%)

**Status:** Open
**Added:** 2026-10-20
**Updated:** 2026-10-20
**Summary:** 承接 26-10-01-2157 (91%→96%, Done) 的第二轮: 清偿 `--cov-fail-under=98` 连续多轮飘红的存量欠账, 分 P0/P1/P2 三阶段推到 99% 区间; 防回沉在 M1–M4 之外补 watchlist、豁免治理、工具侧门禁评估
**Topics:** test-coverage-uplift-2
**Refs:** memory-bank/plans/26-10-20-2101-plan-test-coverage-uplift-2.html

## 原始请求

「制定一个测试覆盖率提升分阶段执行计划」——在已有测试体系(全套件 + `--cov-fail-under=98` 门槛 + 基线切片机制)之上, 给出可分段执行、可分段验收、带防回沉机制的覆盖率提升路线。

## 思考过程与决策

- **先实测再立计划**: 全量跑一遍拿最新缺口(2026-10-20 test.full, develop), 不用历史估值。本计划一切数字都是这一轮实测, 缺口地图与预估单位按 §1 换算口径推导。测试条数与耗时口径见 `commands run kb.baseline` 最新切片, 本档案不手抄。
- **发现了「门槛飘红」这个比数字本身更重要的事实**: `--cov-fail-under=98` 已连续多轮 FAIL(基线切片留痕, 属既有欠账非本轮引入, 全量用例 0 failed)。所以第二轮的核心目标不是「再涨几个点」, 而是**先把门槛真正脑血管绿, 且绿得有余量** —— 否则每轮全量都顶着一根红线, 阈值形同虚设。
- **为什么不一步到位抬到 99% 再冲**: heden 阶段闸门惯例(阈值恒低于当期实测约 0.3–1 个点, 给并行 `-n 8` 分支 partial ±1 的口径波动留余量)。本计划阈值阶梯: P0 后维持 98 → P1 后 98.5 → P2 后 99。与上一轮 M1 同一纪律, 只是把「低于 1 个点」细化为分档。
- **P0 主攻选 tool_client 而不是大文件**: `webui/tool_client.py` 行覆盖 79%, 全仓最低, 且缺的是 `call_tool` 整块 HTTP 契约(密度最高、一次能 +24); 大文件 relocate_mod (79 单位) 放 P1 —— 它散布错误路径, 单块密度低, 放快赢轮会拖慢验证节奏。
- **机制侧新增三项而不是重抄上一轮**: watchlist(单文件 <95% 清单进每轮基线复查)、豁免治理(pragma 行数进切片, 只减不增)、工具侧(gtm)门禁评估 —— 上一轮机制 M1–M4 保留延续, 不重复提案。

## 实现计划

1. 立本档案 + 计划制品(`plans/26-10-20-2101-plan-test-coverage-uplift-2.html`, Open) + 双向认领 + 索引重生成。
2. P0 清偿门槛: tool_client HTTP 契约 / commands.py 早退参数化 / finalize_watch 三证平台分支 / 零碎小件 → TOTAL ≥ 98.3% 且门槛转绿 → 基线切片。
3. P1 traffic 家族与 relocate 中坚: relocate_mod / traffic_store / traffic_sample_mod / traffic_source/agent / alias_fs / traffic_grid → TOTAL ≥ 98.7% → 阈值抬 98.5 → 基线切片。
4. P2 长尾与 watchlist 清零: validation/utils/grouping/hr/config 尾 + tray 残留 → TOTAL ≥ 99.2% → 阈值抬 99 → 计划转 Done。
5. P3 防回沉常态化: M1–M7 随阶段验收落地, watchlist 与豁免数字进每轮切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 0 | 立档 + 计划制品 + 认领链 + 索引重生成 | Done (2026-10-20) |
| 1 | P0 · 清偿 98% 门槛与快赢轮 | Pending |
| 2 | P1 · traffic 家族与 relocate 中坚 | Pending |
| 3 | P2 · 长尾清偿与 watchlist 清零 | Pending |
| 4 | P3 · 防回沉机制落地与常态化 | Pending |

## 进度日志

### R0 · 立档 (2026-10-20)

实测 2026-10-20 test.full 全量(develop): 全套件 0 failed(条数与耗时见 kb.baseline 最新切片), TOTAL 97.66%, 门槛 98% FAIL —— 存量欠账, 非本轮代码引入。覆盖分母 = 语句 + 分支出口 ≈ 27,683 单位, 未覆盖 633 单位; 每单位 ≈ 0.0036%。

缺口集中度: core 244 / webui 206 / infra 61 / config 48 / hr 47 / tools 17 / rules 6 / tray 3 / torrents 1。单文件 Top13 合计 433 单位 = 68% 总缺口(relocate_mod 79 / tool_client 60 / commands.py 48 / traffic_store 40 / traffic_sample_mod 38 / …)。形态上: HTTP 契约整块空洞(tool_client.call_tool 89-112)、 commands.py 的 32 条 `->exit` 早退 partial、子进程·端口·`/proc`·网络探测类外部依赖。

计划按「先清偿门槛(P0, +130±40) → 中坚(P1, +180±50) → 长尾(P2, +180±60)」推进, 终点 99% 区间; 全部任务、落点测试文件与验收 DoD 见计划 §3; 纪律纪律见 §4(坑清单), 机制见 §5(M1–M7)。

- 2026-10-20 21:21 覆盖率第二轮计划制品入库: 立计划(plans Open) + 认领档案, 双向认领链与索引重生成
