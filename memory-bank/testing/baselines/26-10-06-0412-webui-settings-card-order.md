# 2642 —— 设置页分区卡片顺序调整 (站点前置 / 限速·HR 后置)

> 摘要: 用户要求设置页重排 —— 「站点」提到第二位(紧跟「常规」), 「限速」「HR 在线核实」后置到末尾。
> 设置首页卡片 = schema.groups 一对一映射, 单点改 `config/schema/groups.py` 的 GROUPS 元组顺序;
> 前端(config_hub.js::hubCards/hubHits/hubBlocks 按数组序渲染)零改动, 守阵
> `tests/test_web.py::test_config_schema_endpoint` 的分组序列断言同步更新(**原地改写断言, 不增删用例**)。
> 实测 2642 passed + 4 skipped / 99% / 58.50s。
> 基线时间: 2026-10-06 04:12

**Refs:** memory-bank/activeContext/26-10-06-0345-webui-settings-card-order.md

- 分支: develop @ f9a6d6ab (+ 本轮未提交改动: `src/auto_qb/config/schema/groups.py` + `tests/test_web.py`)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2642 passed + 4 skipped, 覆盖率 TOTAL 99%**
  (15916 语句 / 167 未覆盖 / 5442 分支 / 143 partial; 门槛 98% 达标)
  —— 本轮两次采样 58.50s / 50.53s(引擎 60.3s / 52.2s) ⇒ 耗时区间约 **50~60s**。
- 相对上一条基线 [26-10-06-0144](26-10-06-0144-full-code-review-remediation-s0-baseline.md)
  (2622 passed + 4 skipped @ fb461fea, 15624/166/5400/139): passed **+20**, 语句 15624 → 15916(+292),
  未覆盖 166 → 167(+1), 分支 5400 → 5442(+42), partial 139 → 143(+4)。
  ⚠ **这 +20 用例不是本轮改动带来的**: `fb461fea..f9a6d6ab` 之间有 9 个 commit(6 个含代码/测试改动 ——
  规则表达式修复 / load_grouping_config 修复 / qB 流量 v4 两批 / qb_capture 修复 / S2 批修复;
  另 3 个为计划/文档/基线), 用例与源码增量来自它们。本轮只**原地改写**一条断言, 不增删用例 ⇒
  passed 相对 HEAD(f9a6d6ab) 不变, 差异全部归属中间 commit。
- 靶向: `tests/test_web.py -k config_schema_endpoint` → **1 passed**;
  `tests/test_config_schema.py` + `tests/test_config_key_surface.py` → **39 passed**。
- 改动面: `src/auto_qb/config/schema/groups.py`(GROUPS 元组重排: basic → trackers → maintenance →
  traffic → rules → speed → hr_check, 另加两处说明注释) · `tests/test_web.py`
  (test_config_schema_endpoint 分组序列断言 + 注释)。
