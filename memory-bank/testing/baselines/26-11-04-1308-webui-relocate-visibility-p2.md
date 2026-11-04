# 5176 passed + 10 skipped(根) —— WebUI 迁移可见性 P2(路径链探测与浮窗)完成后全量

> 摘要: WebUI 迁移可见性 P2(路径链探测与浮窗)完成后全量
> 基线时间: 2026-11-04 13:08
**Refs:** memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html

## 验收数字

- `commands run test.full` 实测(2026-11-04 13:14, 150.2s, P2 路径链端点/浮窗完成后): **5176 passed + 10 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 24296 stmts / 226 miss / 8310 branches / 169 partial / **99%**
- 针对性: `uv run pytest tests/test_webui_relocate_chain.py -q -o addopts=""` 13 passed; 三个新模块 `relocate_chain.py`(webui)/`server/routes/relocate_chain.py` 各自 100% 行覆盖, `infra/alias_fs.py` 新增探测段(643-741)零漏行。

## 本改动面

- `src/auto_qb/infra/alias_fs.py`: 新增 `PathInspection` 与只读 `inspect_path`(reparse tag 区分 junction/symlink、硬链接 `st_nlink`、挂载点 `st_dev`、错误分类);`strip_device_prefix`/`resolve_link_target` 处理 `\??\`、`\\?\UNC\`、相对链接与卷设备路径。
- `src/auto_qb/webui/relocate_chain.py`(新): 逐跳探测(8 跳上限/环检测/范围外/未确认)、job `alias_paths` 归属章、TTL 20s + LRU 128 缓存(键 = hash+起点+generation,`refresh` 绕过)。
- `src/auto_qb/webui/server/routes/relocate_chain.py`(新): `GET /api/relocate/chain?hash=...` 只收 40/64 位 hash;起点由服务端从 `root_path`/`content_path`/`save_path` 派生;沿用 `_require_relocate` 403 与 `browse_roots()` 白名单;Mapped/UNC 不做 syscall。
- `src/auto_qb/webui/server/routes/__init__.py`/`fs.py`: 注册新路由;导出 `browse_roots` 单点供复用。
- `src/auto_qb/webui/static/shared/relocate_chain.js`(新): 浮窗状态/取数/定位/文案/复制/焦点回退;四皮肤 script 清单与 `app.js` mixin 接线。
- `src/auto_qb/webui/static/shared/`: `decorate.js` 徽标点击同时打开浮窗;`drawer_rows.js` + `drawer_tpl/01`/`02`/`03` 详情「路径链」入口;`tpl/popovers.html` teleport 浮窗;`row_lang.css` `.relc-*` 样式(z-index 140/141);`lifecycle.js`/`dialogs_meta.js`/`shortcuts_engine.js` Esc 退栈与忙态。
- `tests/test_webui_relocate_chain.py`(新 13 例): 端点门控/只收 hash/路径注入/逐跳类型与归属/环与 8 跳/TTL+refresh/映射与远程/起点派生与环境/错误分类与链接形态/前端静态与 Node 文案。
- `tests/test_web_route_manifest.py`/`tests/test_webui_static_skins_widget.py`: 路由金清单 + teleport 计数随新增面更新。
