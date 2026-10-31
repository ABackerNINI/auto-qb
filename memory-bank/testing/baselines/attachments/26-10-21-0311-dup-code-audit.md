# 3974 passed + 2 skipped —— 前端配置实体增/改/删骨架 9 处收敛为三骨架(issue 26-10-20-2231)

> 摘要: 前端配置实体增/改/删骨架 9 处收敛为三骨架(issue 26-10-20-2231)
> 基线时间: 2026-10-21 03:11
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-config-entity-crud-dup.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20715     75   7012     88    99%
3974 passed, 2 skipped in 138.84s (0:02:18)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 本轮**纯前端 JS 重构, 零 Python 改动、零新增用例** —— 用例数与前一条基线持平, 数字变化只来自前序轮次的存量。
- 前端这一面没有自动化测试面(Python 套件不覆盖 static JS, e2e 无设置页 CRUD 用例), 故行为等价性靠一次性 harness 自证:
  `tmp-analysis/verify-entity-crud.js`(已 gitignore、不入库)以 vm 加载两个 mixin、桩掉 promptDialog/confirmDialog/toast,
  50 项断言覆盖九处入口(增 3 / 改 2 / 删 4), **对改前(HEAD 版)与改后各跑一遍, 均 50/50 通过**。
  断言面: 对话框标题/占位/okText、键序保持、选中键回落、空 `trackers` 段一并收走、`_rules` 后缀、重名 toast、取消/空名/同名静默。
- harness 在开发中抓出一处真回归(后缀规范化算在 def 构建时的空占位名上 ⇒ 新增规则集不补 `_rules`), 改 `normalize` 钩子在骨架调用点生效后转绿 —— 这正是「先写等价性断言再改」的价值。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/config_editor.js` | 新增 `cfgEntityAdd` / `cfgEntityRename` / `cfgEntityRemove` 三骨架 + `cfgTrackerDef` / `cfgRuleGroupDef` / `cfgRuleDef` 三份差异清单; 九处入口收敛为 def 声明 + 一行调用; 删中间态 `newTrackerName` / `newRuleGroupName` / `newRuleName` / `cfg.addOpen` / `cfgAddCancel()` / `cfgTracker(name)`(+131 / −101 行) |
| `src/auto_qb/webui/static/shared/config_hub.js` | 三处 promptDialog 包装合并为 `hubAddEntity(def)`(+27 / −22 行) |
| `memory-bank/issues/26-10-20-2231-refactor-fe-config-entity-crud-dup.html` | 状态 Open → In Progress → Done; 补「修复后补充」(实际修法 / 与建议的差异 / 验证方式) |
| `memory-bank/systemPatterns/web-config-editor.md` | 修「新增交互」那条的陈旧描述(就地展开输入框 → promptDialog / hubAddEntity); 新增「命名实体增/改/删单点」条 |
