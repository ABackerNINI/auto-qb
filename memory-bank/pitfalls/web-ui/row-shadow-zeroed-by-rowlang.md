# 皮肤 CSS 给行加 box-shadow 会被 row_lang flat 归零

> 摘要: 皮肤 CSS 给行加 box-shadow 会被 row_lang flat 归零
> 触发: 行高亮不生效, box-shadow 无效, 右键目标不可见, row_lang, ctx-src
**Refs:** memory-bank/tasks/26-11-03-webui-ctx-src-target-marker.md

### 皮肤里给 `.ctx-src` 行写 `box-shadow` 会静默不生效(atlas 实测恒 `none`)

- **触发**: 在 `static/<皮肤>/css/components.css` 里给 `.group-row.ctx-src` 之类行级标记加 `box-shadow` 高亮(如右键目标行), 以为能框住行。
- **判别**: 浏览器实测 `getComputedStyle(row).boxShadow === "none"`, 但规则确实被加载、选择器也确实命中。根因是 `shared/row_lang.css` 的 flat 行语言: `html[data-rowlang]:not(...):not(...) .rl-scope .group-row { box-shadow: none }`, 特异性远高于皮肤里的 `.group-row.ctx-src`, 且该文件在皮肤 `components.css` 之后加载。prism 某些主题(不进 flat 分支)能生效, 于是"一个皮肤有效、另一个皮肤没有"最容易误判成缓存或浏览器差异。
- **处置**: 行级标记不要用 `box-shadow`, 改用 `outline`(不参与该规则级联): `outline: 2px solid var(--accent); outline-offset: -2px`。同时**不要用左条**: flat 行语言的选中条就是 `--accent` 3px 左条(`.group-row.selected::before`), 同几何同色会被读成"已选中"。`outline` 也是唯一能同时与选中底色、`.kb-cursor` 1px 虚线区分开的低成本属性。若必须用 `box-shadow`, 只能放进 `shared/row_lang.css` 并镜像同款高特异性前缀, 属高成本方案。
- **守阵**: `tests/test_webui_static_skins_table.py::test_frontend_ctx_src_target_marker_parity`(四皮肤四行类 `.ctx-src` 必须是静态实心 2px outline, 且规则体内禁 `box-shadow`/`background`/`--sel-*`/`animation`, 四皮肤逐字同值)。
- **复发**: 0
