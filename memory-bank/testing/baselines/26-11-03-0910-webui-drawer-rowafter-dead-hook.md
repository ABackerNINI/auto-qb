# 4936 passed + 2 skipped(根) —— 抽屉 dtRowAfter 死链修复后全量基线

> 摘要: 抽屉 dtRowAfter 死链修复后全量基线
> 基线时间: 2026-11-03 09:10
**Refs:** memory-bank/issues/26-11-03-0802-bug-drawer-rowafter-dead-hook.html, memory-bank/activeContext/26-11-03-0852-webui-drawer-rowafter-dead-hook.md

## 验收数字

`commands run test.full` 实测(同步远端 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22785    134   7736    128    99%
4936 passed, 2 skipped, 3 warnings in 159.86s (0:02:39)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `src/auto_qb/webui/static/shared/tpl/xtpl.html`: 桥表 `.group-table` 的 `@vue:mounted` 由
  `dtRowAfter($root.dtBridgeTbl(tab), $event)` 改为 `dtRowAfter(tab, $event)` —— 传页签 key, 与
  `dtBridgeDef`/`dtBridgeTbl`/`dtBridgeSegs` 等桥方法「只认页签 key」的契约对齐(issue 26-11-03-0802)。
- `tests/test_webui_static_dom_panel_drawer.py`: 新增 `test_drawer_tpl_row_after_hook_wiring`
  (静态钉模板调用点 + node 电池双参数对照: 传 tab 命中 rowAfterFn、传 table id 不命中), 已登记文件头部
  「## 测试计划」。
- `drawer_templates.js` 零改动; 无 CSS/浮层改动。
