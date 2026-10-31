# 4032 passed + 2 skipped —— 3d+ 流量图空闲零值区活尾合成

> 摘要: 3d+ 流量图(agg 段窗)空闲零值区显示「无采样」的修复 —— 活尾发布补「开放游程合成段」
> 基线时间: 2026-10-29 02:42
**Refs:** memory-bank/plans/26-10-29-0231-plan-qb-traffic-agg-idle-zero.html

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4032 passed, 2 skipped in 159.73s (0:02:39)**
- TOTAL 表: `21066  99   7130   102    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标, 无 FAIL 行; 零失败零回归
- 命令包装层计时 161.6s(含收集与覆盖率报表); 本轮多次全量实测区间约 **150–171s**

定向池单跑(本次改动的两个守阵文件, `--no-cov`): **161 passed in 12.18s**

- `tests/test_traffic_sample.py` —— 本轮 +8 条守阵(切段纯函数 / z 游程合成 / n 游程留 null /
  无信用与无游程不出样本 / 8 小时空闲合成接线 / totals 单调不变量 / 跨本地日界 / 端到端发布)
- `tests/test_traffic_grid.py` —— 读侧合流既有守阵零改动零回归

口径注记: passed/skipped/覆盖率数字由 agent 从本次实测输出誊写; 相对上基线的逐位对比不写
(看差值 `commands run kb.baseline -n 2`)。

## 本改动面

活尾发布面补一条与 raw 段同构的合成路径, 无存储格式 / 配置键 / 前端改动:

- `src/auto_qb/core/modules/traffic_sample_mod.py` —— 新增模块级纯函数 `_hour_spans`(按小时界
  切段)与 `_open_run_hour_samples`(未结算 credit + 开放游程 -> hour 桶样本, 每段 1 条);
  `_pending_agg_rows` 签名加 `run` 并改吃 `agg.pending` 的副本(累计器本体不动);
  `_publish_live_tail` 传 `run`; 三处 docstring 回写新口径
- `src/auto_qb/core/traffic_store.py` —— `LiveTail.pending_agg` docstring 补「含开放游程合成段」
  与 totals 末端锚点不变量(仅注释, 代码零改动)
- `tests/test_traffic_sample.py` —— +8 条守阵; 6 处既有 `_pending_agg_rows` 调用点同步签名;
  头部「## 测试计划」清单登记
- `memory-bank/plans/26-10-29-0231-plan-qb-traffic-agg-idle-zero.html` —— 计划文档(R1 记录实现期
  两处偏差: 无游程不出样本、单段取末端锚点)
- 前端 / 配置 / 落盘格式: 零改动
