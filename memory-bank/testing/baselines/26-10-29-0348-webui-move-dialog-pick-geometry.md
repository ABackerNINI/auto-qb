# 4006 passed + 2 skipped(根) —— webui-move-dialog-pick-geometry 七修: 落点归属(组件根 click.stop)

> 摘要: webui-move-dialog-pick-geometry 七修: 落点归属(组件根 click.stop)
> 基线时间: 2026-10-29 03:48
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md, memory-bank/pitfalls/web-ui/combobox-focusout-close.md, memory-bank/pitfalls/testing/smoke.md

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4006 passed, 2 skipped in 162.56s (0:02:42)**
- TOTAL 表: `20981  98   7088   100    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标(99.28%), 无 FAIL 行; 零失败零回归
- e2e 单跑(`commands run dev.e2e -- move-dialog-fit --grep 按下与抬起`, 双皮肤): **2 passed (12.7s)**
- e2e `@fast` 全量: **224 passed (7.6m)**(上基线 222 → 本轮 +2 = 新增用例 × 双皮肤)
- 红验实测: 摘掉组件根的 `@click.stop` ⇒ 静态 1 红(断言原文见守阵) + e2e 双皮肤红
  (`Error: 按下在输入框、抬到行内留白不得收起面板…` / `element(s) not found`); 恢复 ⇒ 全绿
- 取证数字(排查本轮「回归」报告, prism 无焦点): 抬到输入框下 6px ⇒ click target `div.add-input-row` ⇒
  面板 false; 抬到候选行 ⇒ `div.add-input-row` ⇒ false; 抬到上方说明文案 ⇒ `div.add-dialog-body` ⇒
  false(这一路**应当**关)。12 条交互序列 × 5 视口 × headless/headed 在修复前也全绿 —— 证明"旧桩进程
  里的那份资源"才是当次假回归的来源(见 pitfalls/testing/smoke.md 复发 1)

## 本改动面

本轮落点: 1 个源文件 + 2 个测试件 + 2 份坑档。

- `src/auto_qb/webui/static/shared/tpl/combo-input.html` —— 组件**根** `.add-input-row` 增 `@click.stop`
  (落点在本组合框内部的一切点击不再冒泡到 lifecycle 的 window 收层名单); 头注补「七修」一条口径。5 个调用点零改动
- `tests/test_webui_static_dom_panel.py` —— `test_frontend_add_combo_label_clear_mask_and_refit` 新增第 7 节
  (输入行根必须带 `@click.stop`, 并注明只许挂组件根); docstring 补第 7 条口径
- `e2e/move-dialog-fit.spec.mjs` —— 新增「按下与抬起落在不同元素 · 面板不收起」(双皮肤): 变体 A 抬到行内留白、
  变体 B 抬到候选行(面板都得在、输入框不得回填) + 反向守门(真点到组件外仍须收层); 头注补七修口径与断言 ⑦
- `memory-bank/pitfalls/web-ui/combobox-focusout-close.md` —— 第七轮条目(click target 是 down/up 公共祖先)
- `memory-bank/pitfalls/testing/smoke.md` —— 新增「回归的第一嫌疑是验错对象: 旧桩进程 / 旧页签」(复发 1)
