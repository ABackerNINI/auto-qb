# 5134 passed + 10 skipped(根) —— issue 0504 DOM 电池活性修复回归全量

> 摘要: issue 0504 DOM 电池活性修复回归全量
> 基线时间: 2026-11-04 07:23
**Refs:** memory-bank/issues/26-11-04-0504-test-webui-normalize-dom-battery-vacuous.html

## 验收数字

`commands run test.full`（2026-11-04，本 clone，develop @ 804c1670 + 本轮未提交改动）实测：

```text
test.full (170.2s)

TOTAL                                                23937    228   8184    170    99%

5134 passed, 10 skipped in 167.70s (0:02:47)
```

口径注记：

- 列依次为 statements / miss / branches / partial / cover，即 `23937 statements · 228 miss · 8184 branches · 170 partial · 99%`。
- 汇总行 `5134 passed, 10 skipped`，无 failed / xfail / error。
- 复跑两次（5.43s 单测面与 196.5s 全量面）汇总行与 TOTAL 行逐位一致，无偶红。

## 本改动面

- `tests/webui_dom_page_support.py`
  - `_NODE_RULE_TREE_PROBE` 条 1（扁平 conditions 包隐式 all）：改为红验式三步 —— 先钉输入为扁平列表 → 调 `cfgNormalizeRulesDraft()` → 再钉变成 `{all:[...]}`，消灭"绿与没跑不可判"。
  - 同电池条 5（幂等）：原 `(f(), f(), true)` 丢弃返回值恒真，改为整棵 `example_rules` 归一前后快照 `J()` 深比较；新增"幂等比较模式活性专桩"一条，喂非幂等样本自证该比较模式必红。
  - 探针尾部：支持 `process.argv[3] === "liveness"` 注入一例必红期望（正常运行不含，不改变既有 16+ 项计数）。
- `tests/test_webui_static_dom_page_layout.py`
  - `test_frontend_rule_tree_and_choose_editor` 第 5 步端到端活性探针：带 `liveness` 二次运行，断言 `total == 正常轮 + 1` 且注入的红精确出现在 `failed`（坑档 `pitfalls/testing/guard-dead-branch.md` 手法）；docstring「本守阵钉」补第 5 条与归一条目红验式说明。
