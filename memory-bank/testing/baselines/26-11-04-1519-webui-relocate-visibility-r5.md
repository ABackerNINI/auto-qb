# 5185 passed + 10 skipped(根) —— WebUI 迁移可见性真机验收(RM04-15..18)完成后全量

> 摘要: WebUI 迁移可见性真机验收(RM04-15..18)完成后全量
> 基线时间: 2026-11-04 15:19
**Refs:** memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html, memory-bank/tasks/26-11-04-webui-relocate-visibility.md

## 验收数字

- `commands run test.full` 实测(2026-11-04 15:16, 238.2s; pytest 汇总 171.65s, 真机用例已在此前单独跑过、不在本全量内): **5185 passed + 10 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 24363 stmts / 228 miss / 8344 branches / 171 partial / **99%**
- 针对性真机用例(分支 `feat/webui-relocate-visibility`, HEAD `3dd603f9`, 均 `commands run real.run -- --case … --yes`): `RM04-15` 51.1s PASS; `RM04-16` 30.2s PASS; `RM04-17` 70.0s PASS; `RM04-18` 38.2s PASS; 回归 `RM04-14` 34.3s PASS

## 本改动面

- `tests-real/rm04_relocate/test_rm04_relocate_visibility.py`(新): RM04-15 四皮肤行高/徽标几何 + 浮窗定位/滚动关闭/Esc 退栈 + 组行入口基准 + armed 并组; RM04-16 A→B→C 逐跳类型/状态/归属章、10 级 junction 长链、UNC 不可达快速返回; RM04-17 pending_tag 生命周期; RM04-18 pending_tag 关闭零写。
- `tests-real/lib/relocate_visibility_ui.mjs`(新): Playwright 取证脚本(四皮肤测量、合成底锚翻转、左右夹取、真实表格/页面滚动关闭、长链内滚、Esc 焦点回归、drawer 入口基准)。
- 复用 `tests-real/rm04_relocate/test_rm04_relocate.py` 的造种/清场/`cmd_post_and_wait`/job 相位助手; 未改产品代码、配置与既有用例。

## 文档回写

- 任务档案 `memory-bank/tasks/26-11-04-webui-relocate-visibility.md`(新立档, 阈值命中);
- 计划 `memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html` §10 追加 R5;
- 会话切片 `memory-bank/activeContext/26-11-04-1047-webui-relocate-visibility.md` 追加 R5 并收尾。
