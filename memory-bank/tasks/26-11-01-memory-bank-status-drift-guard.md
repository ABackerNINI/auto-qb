# 26-11-01-memory-bank-status-drift-guard — 状态漂移机检落地与存量清零

**Status:** Done
**Added:** 2026-11-01
**Updated:** 2026-11-02
**Summary:** 状态漂移机检四档判据落地并联入提交闸门与 kb.wrap; 存量 B/C/D 清零(硬拦归零, 合法滞留+误报留档理由齐档)
**Topics:** memory-bank-status-drift-guard
**Refs:** memory-bank/testing/baselines/26-11-02-2039-memory-bank-status-drift-guard.md

## 原始请求

1. 「有些档案老是实际已完成但状态仍为 open,有没有机检流程可以盯住」——要求对方案 grilling 压测后落地。

## 思考过程与决策

grilling 逐轮拍板:判据分层(progress 反链=高置信、正文完成断言=低置信);发现后动作分档(高置信硬拦、低置信只列不拦、不自动翻状态);挂点 kb.check(进提交闸门)+kb.wrap 收尾清单双点;范围全四族(tasks/issues/plans/reports);守卫先行、存量当实证样本、清零收尾(无冻结名单);badge/meta 双写一致性一并管。Q11 修订(用户指认"部分完成待真机"误报类):高置信按目标状态再分层——反链×Open 才硬拦(整段忘翻),反链×In Progress 降为列表(合法滞留区),豁免走状态语义不建标记词表。

## 实现计划

1. T1 判据脚本 `check_status_drift.py`(四档判据+异常档+CLI+测试计划 docstring)。
2. T2 守卫测试(合成夹具全覆盖)+ T3 kb.check 第 9 条/提交闸门接线 + wrap 尾部清单。
3. T4 实测存量出清单,报用户拍板。
4. T5a 清零 B 档+C 档裁决;T5b D 档逐文件取证裁决。
5. 分支串行 commit,ff 回 develop 后随主提交入库。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| T1 | 判据脚本 check_status_drift.py | Done(2026-10-31) |
| T2+T3 | 守卫测试+kb.check/闸门接线+wrap 集成 | Done(2026-10-31) |
| T4 | 存量实测出清单 | Done(2026-10-31) |
| T5a | B 档清零+C 档裁决(badge 对齐 Done;drawer 翻 Done;config-eol 合法滞留) | Done(2026-11-01) |
| T5b | D 档 62 条裁决(seed-state 翻 Done,余 46 条确证误报留档) | Done(2026-11-01) |
| T6 | 低置信输出收敛(C/D 默认仅一行计数, --verbose 展开; 守卫与 wrap 同步) | Done(2026-11-02) |

## 进度日志

### R0 · 立档 (2026-11-01)

机检四档判据落地并联入守卫体系;存量 B/C/D 全部处置完毕(硬拦归零,合法滞留与误报均已记录理由),checker 与 kb.check 全绿;测试基线见 kb.baseline 最新切片。

- 2026-11-01 00:16 状态漂移机检四档判据落地联入守卫体系, 存量 B/C/D 清零(硬拦归零, 合法滞留+误报留档)

### R1 · 低置信输出收敛 (2026-11-02)

T5b 结论(余 46 条 D 档确证误报)已足够证明低置信面的信噪比问题: 每轮裸跑都要展开 47 行, 而无一需要翻状态。本轮把 C/D 默认输出收敛为一行计数(`== <tier>: N (--verbose to unfold per-row detail) ==`), 详情挂 `--verbose` 显式开关; Tier A/B/anomalies 高置信仍逐条 (硬拦语义与退出码零改动)。kb.wrap 尾部同步收敛(`[C 清单] N 条 (--verbose 展开详情)`), 并改守卫三条(两条 C/D 闸门测试 + wrap 集成测试): 默认模式断言不出条目正文, --verbose 断言逐条仍可展开。

- 2026-11-02 20:30 低置信 C/D 清单默认收敛为一行计数并新增 --verbose 展开详情, A/B/anomalies 高置信逐条不变
