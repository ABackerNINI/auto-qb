# 4897 passed + 10 skipped(根, 99%) —— 右键目标行持续可见标识修复后全量基线

> 摘要: 右键目标行持续可见标识修复后全量基线
> 基线时间: 2026-11-03 00:32
**Refs:** memory-bank/tasks/26-11-03-webui-ctx-src-target-marker.md

## 验收数字

`commands run test.full` 实测(根套件):

- 汇总行: `4897 passed, 10 skipped, 3 warnings in 221.78s (0:03:41)`
- TOTAL 表: `22523 语句 / 152 未覆盖 / 7728 分支 / 134 部分覆盖 / 99%`
- 口径: 在同步后的 `96935f48` 工作树上热跑; 本轮新增守阵 `test_frontend_ctx_src_target_marker_parity` 计入 passed。

## 本改动面

- `src/auto_qb/webui/static/prism/css/components.css`: 行级 `.ctx-src` 改 `outline: 2px solid var(--accent); outline-offset: -2px`。
- `src/auto_qb/webui/static/atlas/css/components.css`: 同值(附失效机理注释)。
- `src/auto_qb/webui/static/console/css/components.css`: 同值(防漂移)。
- `src/auto_qb/webui/static/flux/css/components.css`: 同值; `fx-row-flash` 保留为入场动效。
- `tests/test_webui_static_skins.py`: 新增 `test_frontend_ctx_src_target_marker_parity`(四皮肤四行类覆盖 + 静态 outline + 禁 box-shadow/左条/底色/`--sel-*`/animation + 四皮肤同值), 并同步头部「## 测试计划」清单。
- 未改共享 JS、选区/锚点/焦点语义; 无后端与配置改动。
