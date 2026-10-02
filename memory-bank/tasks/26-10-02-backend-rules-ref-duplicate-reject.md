# 26-10-02-backend-rules-ref-duplicate-reject — 站点引用规则拒绝重复

**Status:** Open
**Added:** 2026-10-02
**Updated:** 2026-10-02 16:31
**Summary:** 新 feat: trackers.<站点>.rules 引用判重。分析结论: 重复引用零实际用途(运行时 _resolve_refs 按规则名去重, 引用语法无次数/权重语义), 纯误操作产物 → 配置校验层拒绝 + WEBUI 下拉防呆。计划 plans/26-10-02-1621 待拍板(拍板点 A 报错 vs WARN / B 只拒收不静默去重), 四波次 W1 校验判重 / W2 前端防呆 / W3 文案四处 / W4 测试。
**Topics:** rules-ref-duplicate-reject
**Refs:** memory-bank/plans/26-10-02-1621-plan-rules-ref-duplicate-reject.html

## 原始请求

用户: 「新feat: 站点引用规则时拒绝重复, 先分析重复规则是否有可能的实际用途, 写一份修改计划」。

## 思考过程与决策

- **消费链取证**(基线 c02e9e14): 校验 `validation/rules.py:54-68 _check_rule_refs` 只查 @ 前缀与存在性; 运行时 `core/modules/rules_mod.py:377-392 _resolve_refs` 按规则名去重(docstring 明言), interval 任务与 on_* 事件分派都吃去重后列表 → 重复引用完全惰性。
- **用途分析三论据**: ①执行幂等(写两遍不跑两遍); ②无次数/权重语义可表达(interval/execute_once/cooldown 全在规则 spec 侧, 引用是无参字符串); ③无顺序增益。重复只可能是误操作(下拉不过滤已引用项 + 自由文本可粘贴), 应 fail-fast。
- **边缘辨析**: `@A` + `@A.b` 包含重叠同样冗余, 但判集合关系复杂度/误报不成比例 → 非目标。
- **方案取舍**: 归一键用 `str(ref).strip()`(与函数现有归一口径一致, 不折叠大小写); 报错口径对齐 `fs.path_map.from` 判重先例(sections.py:406); 否决「去 @ 后内剥离」归一(只服务病态键名, 报错还丢用户原文); 否决静默去重迁移(黄金法则 2); 否决行内实时红框校验(动 Vue 行级校验面, 收益不成比例)。

## 实现计划

计划文档 [plans/26-10-02-1621-plan-rules-ref-duplicate-reject.html](../plans/26-10-02-1621-plan-rules-ref-duplicate-reject.html), 四波次:

| 波次 | 内容 | 主点 |
|---|---|---|
| W1 | `_check_rule_refs` 第二轮判重 | validation/rules.py:54; 归一 strip + 0 基序号对齐先例 |
| W2 | 前端防呆: 下拉过滤已引用 + refPick 双保险 | config_editor.js refOptions/refPick; 保存报错走既有 toast |
| W3 | 文案同步 4 处 | schema help / 05-console-hub / 04-split-explain / docs/configuration.md:410 |
| W4 | 测试 | test_validate_rule_refs 四例 + test_tracker_rules_ref 运行时去重回归锁 + 冒烟 |

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 用途分析 + 修改计划产出 | Done |
| 2 | 用户拍板(点 A/B) | Pending |
| 3 | W1 后端判重 + W4 测试 | Pending |
| 4 | W2 前端防呆 + 冒烟 | Pending |
| 5 | W3 文案与文档同步 | Pending |
| 6 | 收尾(全量基线 + 回写) | Pending |

## 进度日志

- 2026-10-02 16:31 — 计划轮完成: 同步 c02e9e14 → 证据链取证(校验/加载/运行时/前端/保存五段) → 用途分析(结论: 无用途) → 计划 plans/26-10-02-1621(doc-topic rules-ref-duplicate-reject, Open) → 立档本档案。生产文件零改动, 待拍板后进 W1-W4。
