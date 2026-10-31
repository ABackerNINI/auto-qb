# 3756 passed + 10 skipped(根, 覆盖率 98%) —— 重命名弹窗加宽 860(modal 宽度档位修)后全量基线

> 摘要: 重命名弹窗加宽 860(modal 宽度档位修)后全量基线
> 基线时间: 2026-10-19 22:56
**Refs:** memory-bank/tasks/26-10-19-webui-modal-width-tier.md

## 验收数字

```
TOTAL                                                20327    391   6954    262    98%
3756 passed, 10 skipped in 35.88s
```

口径注记:
- 3756 = 上基线 3747(22:07 切片) + 远端两提交(站点 chip 两槽图标 f7f88cc1 + 实施计划 7ed3d7d8)带入 8 条 + 本轮新增静态守阵 1 条(test_frontend_rename_dialog_width_wiring); 零回归。
- skip 10 条为模式门控存量(与上基线同)。
- 前端侧另有 e2e: fast 门禁 186 passed(含新几何守阵 2 条); 全量 dev.e2e 304 passed / 10 skipped(10.3m; 较上轮 298 的差值 = 远端 site-alerts 4 条 + 本轮 rename-dialog-fit 2 条, 零回归)。

## 本改动面

- `src/auto_qb/webui/static/shared/ui_feedback.js`: `_modalInit` 增 `cls: ""` 附加类选项(空 = 既有对话框零变化)
- `src/auto_qb/webui/static/shared/tpl/popovers.html`: 模态根类绑定并入 `modal.cls`(数组形态)
- `src/auto_qb/webui/static/shared/drawer.js`: `editRename` 传 `cls: "rename-dialog"`(带头注)
- `src/auto_qb/webui/static/{prism/css/components.css, console/css/dialogs.css, atlas/css/dialogs.css}`: 三皮肤成对 `.modal.rename-dialog { width: var(--modal-w-add) }`(860)
- `tests/test_webui_static_dom_panel.py`: 新增 `test_frontend_rename_dialog_width_wiring` + docstring 清单行
- `e2e/rename-dialog-fit.spec.mjs`: 新增, 双皮肤 @fast(860 宽档 + 97 字符长名零裁剪 + 取消零提交; 三断言各自红验)
- 知识库: 新坑档 `pitfalls/web-ui/modal-width-tier.md`
