# WEB UI 产出口径与令牌

> 摘要: 菜单/入口分层、令牌分工、按钮体系、悬浮提示、选中摘要口径、fx 动效库与 flux 皮肤、HTML dark 主题 —— 前端产出口径的唯一出处。各主题已外迁到 `attachments/webui-*.md`, 见下方主题地图。
> 触发: WEB UI 约定, 菜单分层, 令牌, 主题, dark, HTML 产出, tooltip, 悬浮提示, 选中摘要, occ_key, 实际占用, fx, 动效, data-fx, flux, 皮肤, preset, reduced-motion
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-css-rule-family-dup.html, memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html

## 写 WebUI 前必读(硬规则)

- **菜单项是数据不是模板**: 项集注册在 `shared/ctx_menu.js` 的 `CTX_ITEM_DEFS` / `CTX_SUB_ITEM_DEFS`, 模板只 `v-for` 消费; 支名由 `menu.js::ctxMenuKind()` 单点给出; 一级只允许一个次级菜单入口; 多选与单组两条入口的项集必须一致。
- **动作文案 = 动词 + 灰色种子数 N**: N = 实际受作用的种子总数, 计数单点 `selection.js::_seedCountOf`; scope 词(批量/该种子/整组/整剧/整集)不进可见文案。
- **令牌纪律**: 同名语义只允许一个令牌族; 令牌名集三皮肤必须相等; 新增令牌 = 三皮肤同轮补名; 新增弹窗只选 `--modal-w-*` 档位, 不写新数字。
- **按钮与弹窗**: 动作按钮一律 `.bt` 族, `<button>` 显式 `color`; 弹窗按后果等级染色走 `_openModal` 派生 tone, 新对话框不要自己判 danger。
- **busy 骨架**: 只走 `shared/dialogs.js` 的 `_mgrRun` / `_panelLoad` / `_postWaitCmd`, 不手抄; 禁止裸 `toast(..., {sticky: true})` 或用 `_finishToast` 原位改字顶掉进行中条。
- **悬浮提示**: 新元素继续写原生 `title`, 由 `.aq-tip` 委托层接管; 不新造浮层。
- **共用规则族**: 三皮肤逐字节相同的规则族进 `shared/console_hub.css` 尾段单点; 皮肤内保留真差异, 不许顺手抹平。
- **动效隔离**: 走 `data-fx` / `data-fx-preset` + `window.AQB_FX` 单挂载器; 每个 `@keyframes` 配 `prefers-reduced-motion` 降级; atlas/prism/console 对 `shared/fx/` 零引用。
- **HTML 产出**: 一律 dark 主题(深色底 + 浅色字), 样式里必须写 `color-scheme: dark`。

## 主题地图(每节一行, 权威在附件)

- 菜单/入口分层原则 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 菜单/入口分层原则」
- 令牌分工 → [attachments/webui-theme-tokens.md](attachments/webui-theme-tokens.md) 「WEB UI 令牌分工」
- 按钮体系 .bt → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 按钮体系 .bt」
- 弹窗语义配色分级 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 弹窗语义配色分级」
- 三皮肤共用规则族 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 三皮肤共用规则族」
- busy 骨架单点 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI busy 骨架单点」
- 悬浮提示 .aq-tip → [attachments/webui-interaction.md](attachments/webui-interaction.md) 「WEB UI 悬浮提示 .aq-tip」
- 选中摘要口径 → [attachments/webui-interaction.md](attachments/webui-interaction.md) 「WEB UI 选中摘要口径」
- fx 动效库与 flux 皮肤 → [attachments/webui-fx.md](attachments/webui-fx.md) 「WEB UI fx 动效库与 flux 皮肤」
- HTML 文档 dark 主题 → [attachments/webui-theme-tokens.md](attachments/webui-theme-tokens.md) 「HTML 文档一律 dark 主题」
