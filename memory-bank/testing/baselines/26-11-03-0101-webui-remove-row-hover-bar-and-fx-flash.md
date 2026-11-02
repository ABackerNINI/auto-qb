# 4900 passed + 10 skipped(根) —— 四皮肤 hover 左条移除 + flux 右键强调动效退役后全量基线

> 摘要: 四皮肤 hover 左条移除 + flux 右键强调动效退役后全量基线
> 基线时间: 2026-11-03 01:01
**Refs:** memory-bank/tasks/26-11-03-webui-remove-row-hover-bar-and-fx-flash.md

## 验收数字

`commands run test.full` 实测(根套件):

- 汇总行: `4906 passed, 10 skipped, 3 warnings in 209.29s (0:03:29)`
- TOTAL 表: `22531 语句 / 152 未覆盖 / 7732 分支 / 134 部分覆盖 / 99%`
- 口径: 最终合流提交 `cd8ba4eb` 上全量实测; rebase 前本地为 4900 passed(远端 a48ead5c 测试拆分净增 6 个用例后为 4906)。迁移后的 `tests/test_webui_static_skins_{skin,table,widget}.py` 定向实测 27 passed。

## 本改动面

- `src/auto_qb/webui/static/shared/row_lang.css`: 移除 flat/wave 各 2 条 `:hover::before` 左条规则与仅被其消费的 `--rl-bar` 背景声明; 保留选中/半选 `::before` 几何、`--rl-bar-on` 与 transition。
- `src/auto_qb/webui/static/flux/css/fx-mount.css`: 删除 D4-3 `.ctx-src` 的 `fx-row-flash 600ms` 动画规则; 段注同步为「D4-3 退役, 改 `.ctx-src` 静态描边」。
- `src/auto_qb/webui/static/shared/fx/fx.css`: 删除 `[data-fx~="row-flash"]` 规则、`@keyframes fx-row-flash` 与 reduced-motion 降级项。
- `src/auto_qb/webui/static/shared/fx/fx.js`: REGISTRY.effects 移除 `"row-flash"`。
- `src/auto_qb/webui/static/flux/css/components.css`: 仅注释去掉「fx-row-flash 入场」表述; `.ctx-src` 静态实心 2px outline 规则原值不动。
- `tests/test_webui_static_skins_skin.py`(rebase 后远端拆分文件): `test_frontend_fx_wiring` 注册表名数 27 → 26, 头部「## 测试计划」清单同步 row-flash/D4-3 退役。
- 未改共享 JS、模板、选区/锚点/焦点语义; 无后端与配置改动; 合流提交 `c87ef855` + 索引重建 `cd8ba4eb`。
