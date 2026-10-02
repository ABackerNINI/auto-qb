# 站点引用规则拒绝重复（计划轮）

> 摘要: 新 feat 计划轮。分析结论: trackers.<站点>.rules 重复引用零实际用途 —— 运行时 `_resolve_refs` 按规则名去重(rules_mod.py:377), 引用语法无次数/权重语义, 纯误操作产物。计划 [plans/26-10-02-1621](../plans/26-10-02-1621-plan-rules-ref-duplicate-reject.html) 四波次(W1 校验判重 / W2 前端下拉防呆 / W3 文案四处 / W4 测试)待拍板: 点 A 直接报错 vs 先 WARN; 点 B 只拒收、不做静默去重。档案 tasks/26-10-02-backend-rules-ref-duplicate-reject。
> 最后活动: 2026-10-02 16:31

## 正在进行

- 待用户拍板计划(点 A/B) → 拍板后按 W1-W4 实施。

## 本轮产出

- 计划 [plans/26-10-02-1621-plan-rules-ref-duplicate-reject.html](../plans/26-10-02-1621-plan-rules-ref-duplicate-reject.html)。
- 档案 [tasks/26-10-02-backend-rules-ref-duplicate-reject.md](../tasks/26-10-02-backend-rules-ref-duplicate-reject.md)(立档阈值 #4)。
