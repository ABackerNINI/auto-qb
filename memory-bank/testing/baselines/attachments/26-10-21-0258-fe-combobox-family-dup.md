# 3959 passed + 10 skipped (TOTAL 99%) —— 认领修复 issue 26-10-20-2230 前端 combobox 族重复(模板骨架/键盘导航/40ms 收层三面收敛)

> 摘要: 认领修复 issue 26-10-20-2230 前端 combobox 族重复(模板骨架/键盘导航/40ms 收层三面收敛)
> 基线时间: 2026-10-21 02:58

## 验收数字

根(Windows 本机 `.venv` Python 3.14.7, `commands run test.full`, 2026-10-21 02:58, xdist `-n 8`):

```
TOTAL                                                20437     93   6998     92    99%
Required test coverage of 99% reached. Total coverage: 99.30%
3959 passed, 10 skipped in 41.61s
```

口径注记:

- **本轮是重构轮**: 产品码净减 ~100 行模板(五处骨架 → 一处), 用例数未增(守阵 4 条是被**改写**到新结构, 不是新增)。
- **收尾阶段曾 2 红**: `test_kb_index_is_regenerated` / `test_gen_all_check_is_green` 报 `pitfalls/web-ui/_index.md` 漂移 —— 新坑档是由 `kb.new pitfall` 落盘时生成的, 但随后 `kb.wrap` 又动了 tasks 侧, 索引未重跑; 补一条 `commands run kb.index` 后转绿。**教训: 知识库收尾的机械动作顺序里, `kb.index` 必须排在最后一次文档写入之后**(不是每个命令各建一次)。
- 副作用台账越界 0 条。
- Linux 侧本轮未取数字(`test.linux` 未跑; 按 `testing/baseline.md` 常驻警告, 本切片只作 Windows 侧事实源)。
- 前端改动另跑 `commands run dev.e2e` 真浏览器冒烟(结果见同轮切片/档案, 数字不在此处抄第二遍)。

## 本改动面

重构轮(零行为变更, 骨架收敛), 逐文件:

| 文件 | 改动 |
|---|---|
| `shared/tpl/combo-input.html` | **新增独立分片** `#tpl-combo-input`(不并进 `xtpl.html` —— 后者原 381 行, 并入后 455 行超「单分片 400 行」守阵) |
| `shared/tpl/xtpl.html` | 净 0(曾临时并入, 已回退到 381 行) |
| `shared/tpl/dialogs-mgr.html` | 保存路径/分类/标签三块 18-22 行骨架 → 各一行 `<aq-combo-input …>`; label 与 FX-18 注释留在调用点 |
| `shared/tpl/move-dialog.html` | movePath 同款收敛(`inner-list` + `head-text` + `input-ref`) |
| `shared/tpl/popovers.html` | metaCat 同款收敛(`preset-label/preset-value` 的「(无分类)」预置行) |
| `shared/add_torrent.js` | `COMBO_BLUR_CLOSE_MS` + `_popBlurArm`/`_popBlurCancel`; `_comboKeydown(e, kind)` → `comboKeydown(ctx, ev)` **单点并补 IME 守卫**; 新增 `window.AQ_COMBO_INPUT_COMPONENT`(props 16 / emits 6 / methods 5); 三个 `onAdd*Keydown` 降为薄适配器 |
| `shared/dialogs.js` | `metaCatBlurClose` 走 `_popBlurArm` + 删 `_metaPopBlurCancel`; `onMetaCatKeydown` 降为适配器 |
| `shared/drawer.js` | `movePathBlurClose` 走 `_popBlurArm` + 删 `_movePopBlurCancel`; `onMovePathKeydown` 降为适配器 |
| `shared/app.js` | `app.component("aq-combo-input", window.AQ_COMBO_INPUT_COMPONENT)` |
| `atlas/console/prism/index.html` | 三套 shell 的 `tpl-manifest` 同步加挂 `/shared/tpl/combo-input.html`(三套逐项一致) |
| `tests/test_webui_static_dom_panel.py` | 3 条 combobox 守阵 + 1 条 move 守阵改指新结构(读 `combo-input.html` 与调用点属性, 不再读五处骨架) |
| `tests/test_web_backend_misc.py` | 悬停接管守阵改指 `#tpl-combo-input` |
| `memory-bank/pitfalls/web-ui/component-ref-ownership.md` | **新坑档**(组件内字符串 ref 注册在子组件实例 → 根方法读根 `$refs` 恒空; 走方法函数 ref) |

**范围守恒未动**: `tpl/settings.html` 第 6 变体(`hb-tr-*` 类族 + `hubTrackerKeydown`, 守阵独立)不并入; 保存路径仍不挂悬停接管(收敛前即如此)。
