# 6660 passed, 6 skipped —— 全局空闲判据双条件修复收尾全量基线

> 摘要: 全局空闲判据双条件修复(全局系列 z 分类补 totals 持平)收尾全量基线; 3 新用例 + 6 既有用例语义适配 + 1 端到端一致性钉面, 见 kb.baseline 前后链
> 基线时间: 2026-11-21 08:29
**Refs:** memory-bank/tasks/26-11-21-webui-traffic-idle-dual-condition.md

## 验收数字

## 验收数字

`commands run test.full` 实测(2026-11-21 08:26, Windows, HEAD bbb06a58, 收尾回写随工作树在场):

```text
TOTAL                                                30044     74  10662     77    99%
6660 passed, 6 skipped, 8 warnings in 158.99s (0:02:39)
```

- 汇总: 6660 passed / 6 skipped / 0 failed; 覆盖率闸门达标(99% ≥ Windows 阈, 见 testing/baseline.md), 耗时单次采样 158.99s(并行 -n 8)。
- 缺口净额: 本片 151 单位(miss 74 + partial 77) 与上片 26-11-21-0658 的 151 单位(miss 74 + partial 77) **持平净额 0**; 分母由语句 30030 / 分支 10658 变为 30044 / 10662(+14/+4 = 本轮新增生产代码与用例)。本轮代码面 = 采样分类判据 3 单点 + 测试 3 件, 新增面全覆盖(净额 0 = 新增缺口为零)。

## 本改动面

## 本改动面

本轮(全局空闲判据双条件修复)改动面, 逐文件:

- `src/auto_qb/core/modules/traffic_sample_blocks.py`: `_sample_global` 空闲判据补双条件(速率字段 (0,0) 且 totals 与上一观测持平); 新增 `_global_idle_at_totals`(totals 持平判定单点, 游标 = `_ev_prev_obs`)与模块级 `_delta_rate`(差分速率, qB calcRate 同式); totals 变化的零速率字段 tick 重分类 r, dl_rate/up_rate 存差分速率。单种系列零改动。
- `tests/test_traffic_sample_core.py`: 新增 2 用例(协议流量形态逐 tick r / 真静默与协议混合记录序)+ 1 断连重连用例(重分类 r 封 n, 速率=差分/断连实测窗); 6 既有用例语义适配(空闲判据双条件下真静默夹具: 形态 D 两档合流/重置记录改 r/跨天与改间隔封口真静默化); 头部 docstring 测试计划同步 + 既有续行错位修回。
- `tests/test_web_traffic_qb.py`: 新增端到端一致性钉面(5m 全段窗: 磁盘链+活尾两段, GET 与 SSE 事件帧全量 120 帧逐点同值, 修前整窗全 0 的直接复现)。
- `memory-bank/pitfalls/backend/qb-field-basis-mixing.md`: 新坑档(qB 字段口径混杂, 本轮根因单点)。
- `memory-bank/conventions/attachments/webui-traffic-beat.md`: 现行权威节补「全局空闲判据双条件」条。
- 本切片(基线快照)。
