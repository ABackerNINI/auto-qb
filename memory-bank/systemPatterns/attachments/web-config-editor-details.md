# WEB UI 图形化配置编辑 — 外迁细节

> 摘要: `systemPatterns/web-config-editor.md` 的经典设置页死代码清理与 `CE_FIELD_BASE` 契约原文(逐字外迁)。
> 触发: 经典设置页, ce-field, CE_FIELD_BASE, CE_FIELD_COMPONENT, 死模板, CSS 清理

> 本文件是外迁存档: 主档该段原文一字未改搬来, 仅相对链接整体上移一层(本文件在 `systemPatterns/attachments/`)。

## 外迁条目

- **经典页死代码清理(2026-09-25)**: `ce-field` 组件与 `tpl-ce-field` 模板(唯一引用是**自身模板内**的递归, 早已不可达)删除; 其行为基座随之由 `CE_FIELD_COMPONENT` 改名 **`CE_FIELD_BASE`** 并摘掉只服务那个组件的 `name`/`template` 键 —— ⚠ 它**不是组件, 不可再 `app.component` 注册**, 删了 hub 侧会连带失去全部 `cfg*` 读写。守阵 `_scan_mixin_wiring` 的"定义即需接线"已把"被另一个全局 `Object.assign({}, window.X, …)` 拷走"也算作接线(红绿双验过)。连带删除: 只被该模板引用的 **40 个 `.ce-*` 类**(含 `is-pattern` / `ceg-*` 动态类)、**177 条 CSS 规则 / 约 250 行**(atlas `style.css` + prism `components.css`/`views.css`/`base.css`), 以及 `.hb-switch-entry`、`.logs-page` 两处历史遗留死类。判据与验证见 [pitfalls/web-ui/template-render.md](../../pitfalls/web-ui/template-render.md)「删死模板要连带清 CSS」。
