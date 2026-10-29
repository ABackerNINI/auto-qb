# 4006 passed + 2 skipped(根) —— webui-move-dialog-pick-geometry 六修: 面板非交互区不抢焦点

> 摘要: webui-move-dialog-pick-geometry 六修: 面板非交互区不抢焦点
> 基线时间: 2026-10-29 03:14
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md, memory-bank/pitfalls/web-ui/combobox-focusout-close.md

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4006 passed, 2 skipped in 156.44s (0:02:36)**
- TOTAL 表: `20981  98   7088   100    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标(99.28%), 无 FAIL 行; 零失败零回归
- e2e 单跑(`commands run dev.e2e -- move-dialog-fit add-options-recent-order`, 双皮肤): **10 passed**
  - `move-dialog-fit` 4 用例 × 双皮肤全绿(含新增「点面板头/空态不收起」)
  - `add-options-recent-order` 双皮肤全绿(含新增空态文案段)
- e2e `@fast` 全量: **222 passed (7.7m)**(上基线 220 → 本轮 +2 = 新增的头点击用例 × 双皮肤)
- 红验三段实测:
  1. 摘掉面板根的 `@mousedown.prevent` ⇒ 静态 1 红 + e2e「点面板头」双皮肤红(element not found)
  2. 收窄成「只给 `.pop-head` 挂 prevent」⇒「点面板头」**仍绿**、`add-options-recent-order` 空态段双皮肤红
  3. 恢复根级 ⇒ 全绿

## 本改动面

用户「缺陷一并修复」的落点(点面板头「选择保存位置 N」面板就收), 1 个源文件 + 3 个测试件:

- `src/auto_qb/webui/static/shared/tpl/combo-input.html` —— 面板根 `.pop-menu.add-pop` 增 `@mousedown.prevent`(与既有 `@click.stop` 并列); 头注补「焦点纪律」一条 + 面板根处 8 行口径注释(为什么挂根不逐个挂、与候选行修饰符为何不冲突、为何不影响滚轮/滚动条)。5 个调用点零改动
- `tests/test_webui_static_dom_panel.py` —— `test_frontend_add_combo_label_clear_mask_and_refit` 新增第 6 节: 面板根必须同时含 `@mousedown.prevent` 与 `@click.stop`; docstring 补第 6 条口径
- `e2e/move-dialog-fit.spec.mjs` —— 新增「点面板头/空态不收起 · 面板内非交互区不抢焦点」(双皮肤): 点 `.pop-head` 后面板仍在、输入框未改写, 且**随后点候选仍能回填并收起**(防"修成冻住"); 头注补六修口径与断言 ⑥
- `e2e/add-options-recent-order.spec.mjs` —— 末尾补空态段: 先 Esc 收掉路径面板(它朝下展开盖着分类输入框), 点分类输入框 → 填不存在的分类 → 候选过滤到 0 → 点 `.pop-empty` 面板不许收
