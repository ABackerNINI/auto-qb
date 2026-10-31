# 2871 —— 规则卡「触发与节奏」段 + 桩版本章物化基线

> 摘要: 用户报「WEBUI 规则设置只能设置条件与动作」→ 规则卡新增折叠段, schema.rule_fields 六字段全量图形化(cfgRuleMetaItems + hub-field 通用渲染, interval/watch_fields 挂 grey_if); 桩 _materialize_config 物化带版本章配置打通保存流冒烟(PUT 200 + 落盘 spec 正确 + 刷新回读一致, 零 pageerror)。坑档 ×2(show-if-residual-key / harness-save-flow)。
> 基线时间: 2026-10-09 22:19
> 档案: memory-bank/tasks/26-10-09-webui-rule-meta-fields.md

**Refs:** memory-bank/tasks/26-10-09-webui-rule-meta-fields.md,memory-bank/activeContext/26-10-09-2219-webui-rule-meta-fields.md

## test.full 实测

- 分支: `develop`(HEAD `aec6e2e8`; 工作树含本专题 6 文件改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2871 passed + 3 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 38.2s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 增量明细(本轮真正新增): `src/` 5 文件(webui 前端 4 + schema rules.py grey_if×2)与 `scripts/ui_harness.py`(桩物化); pytest 收集面**零新增**(本轮零新测试函数), passed 相对上基线 −1 来自上基线后同枝并入的「详情面板折叠摘除」(22988fce 撤守阵函数), 与本轮无关。
- 冒烟门禁: `npm run test:e2e:fast` **38 passed**(与上基线同收集面, 本轮零新增 e2e); 保存流走一次性浏览器冒烟(.openclaw/tmp, 不入库), 判据在任务档案。
