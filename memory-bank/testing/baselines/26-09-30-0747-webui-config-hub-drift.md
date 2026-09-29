# 基线 · 1829 passed + 3 skipped / 91% —— WEBUI 设置页富说明死条目清理 (config_hub 漂移修复)

**Refs:** memory-bank/tasks/26-09-30-backend-hr-trigger-semantics.md

> 摘要: HR 触发语义重构(87d154c)实施轮发现的范围外漂移, 用户拍板纳入修复:
> `webui/static/shared/config_hub.js` 的 HUB_HELP 富说明表仍挂着 `hr_check.unknown_policy`
> 整条(8 行) —— 该键已随 26-09-28-1932 v3 判定收口删除(迁移链自动清除存量), schema 无此字段,
> 「?」浮窗永不触发, 属误导性死条目; 其 `rel` 引用的「放行有效期」(`verified_ttl`)同为同批
> 已删概念。「还没核实过的种子怎么算」v3 已硬编码为行 4 本地兜底(达标放行·未达标管束),
> 语义说明由 schema `config/schema/hr.py` 的 sites.enabled help 承载(浮窗回退路径可达),
> 无界面信息损失。webui 全量 grep 无其它 unknown_policy / verified_ttl 残留
> (test_hr_resolve 里的引用是「v3 无时效」断言, 合法)。
> 基线时间: 2026-09-30 07:47 (develop @ 87f3437 + 本修复, 先合并远端再收尾)。

TOTAL **1829 passed + 3 skipped / 91%**(12760 语句 / 1012 未覆盖 / 4320 分支 / 428 partial, test.full 25.3s, rc=0) ——
与上基线 26-09-30-1210(1829)通过数持平: 本轮零测试增删, 改动仅为 JS 说明数据删 8 行(不进
Python 覆盖面); 语句计数与本切片实测为准(最新一条 = 单点事实源)。

## 本轮改动面

- src/auto_qb/webui/static/shared/config_hub.js: HUB_HELP 删 `hr_check.unknown_policy` 条目(8 行)。
- 知识库: 本切片 + tasks/26-09-30-backend-hr-trigger-semantics(追记漂移闭环, 子任务 #10 对齐 87d154c) +
  activeContext/26-09-30-0600 切片收口。
