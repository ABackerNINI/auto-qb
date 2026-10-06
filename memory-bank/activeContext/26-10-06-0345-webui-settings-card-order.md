# 设置页分区卡片顺序调整 — 站点前置 / 限速·HR 后置

> 摘要: 用户要求设置页重排 —— 「站点」提到第二位(紧跟「常规」), 「限速」「HR 在线核实」后置到末尾。
> 设置首页卡片 = schema.groups 一对一映射, 故单点改 `config/schema/groups.py` 的 GROUPS 元组顺序;
> 新顺序 basic(常规) → trackers(站点) → maintenance(自动化) → traffic(流量图) → rules(规则) →
> speed(限速) → hr_check(HR 在线核实)。前端(config_hub.js::hubCards/hubHits/hubBlocks 按数组序渲染)
> 无需改动; 守阵 tests/test_web.py::test_config_schema_endpoint 的分组序列断言同步更新。
> test.full 2642 passed + 4 skipped / 99% / 50~60s(基线 26-10-06-0412)。
> 最后活动: 2026-10-06 04:12

**Refs:** memory-bank/testing/baselines/26-10-06-0412-webui-settings-card-order.md

## 现状

- 改动面: `src/auto_qb/config/schema/groups.py`(GROUPS 元组重排 + 两处注释) +
  `tests/test_web.py`(test_config_schema_endpoint 分组序列断言 + 注释)。
- 未立 tasks/ 档案: 单轮小改, 2 文件, 未达立档阈值(≥3 源文件)。

## 关键决策

- 改动单点选 schema(groups.py) 而非前端 hack: 首页卡片 / 搜索直跳 / 风险清单 / 分组标签全部
  由 schema.groups 自动跟随(与 26-09-26 分组合并同一依据, 见 tasks/26-09-26-webui-settings-group-merge.md)。
- 未点名的分区(自动化 / 流量图 / 规则)保持原有相对顺序, 只把站点前移、限速与 HR 后置。
