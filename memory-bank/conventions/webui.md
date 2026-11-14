# WEB UI 产出口径与令牌

> 摘要: 菜单/入口分层、令牌分工、按钮体系、悬浮提示、选中摘要口径、fx 动效库与 flux 皮肤、流量图节拍动效与数值面板、HTML dark 主题、迁移状态展示 —— 前端产出口径的唯一出处。各主题已外迁到 `attachments/webui-*.md`, 见下方主题地图。
> 触发: WEB UI 约定, 菜单分层, 令牌, 主题, dark, HTML 产出, tooltip, 悬浮提示, 键位提示, 键帽, 选中摘要, occ_key, 实际占用, fx, 动效, data-fx, flux, 皮肤, preset, reduced-motion, 节拍动效, 流量图动效, beat, 左移, 扫描束, fx-panel, qbFx, 迁移状态, rel-pair, relocate_pop, --path-src, _pathPositions, 位置集
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-css-rule-family-dup.html, memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html

## 写 WebUI 前必读(硬规则)

- **菜单项是数据不是模板**: 项集注册在 `shared/ctx_menu.js` 的 `CTX_ITEM_DEFS` / `CTX_SUB_ITEM_DEFS`, 模板只 `v-for` 消费; 支名由 `menu.js::ctxMenuKind()` 单点给出; 次级菜单入口由注册表 `kind: "submenu"` 声明(现状「更多操作」+「转移到」两个, 口径见 `attachments/webui-menu-components.md`); 多选与单组两条入口的项集必须一致。
- **动作文案 = 动词 + 灰色种子数 N**: N = 实际受作用的种子总数, 计数单点 `selection.js::_seedCountOf`; scope 词(批量/该种子/整组/整剧/整集)不进可见文案。
- **令牌纪律**: 同名语义只允许一个令牌族; 令牌名集四皮肤(atlas/prism/console/flux)必须相等; 新增令牌 = 四皮肤同轮补名; 新增弹窗只选 `--modal-w-*` 档位, 不写新数字。
- **按钮与弹窗**: 动作按钮一律 `.bt` 族, `<button>` 显式 `color`; 弹窗按后果等级染色走 `_openModal` 派生 tone, 新对话框不要自己判 danger。
- **busy 骨架**: 只走 `shared/dialogs.js` 的 `_mgrRun` / `_panelLoad` / `_postWaitCmd`, 不手抄; 禁止裸 `toast(..., {sticky: true})` 或用 `_finishToast` 原位改字顶掉进行中条。
- **悬浮提示**: 新元素继续写原生 `title`, 由 `.aq-tip` 委托层接管; 不新造浮层。例外(计划 26-11-12-0344 D10/I4): 键位提示不走 title/.aq-tip —— 键帽是常驻 DOM、取数链现算(口径见 `memory-bank/architecture/webui.md`「键位现场提示」节), 仅限键帽面。
- **共用规则族**: 四皮肤逐字节相同的规则族进 `shared/console_hub.css` 尾段单点; 皮肤内保留真差异, 不许顺手抹平。
- **动效隔离**: 走 `data-fx` / `data-fx-preset` + `window.AQB_FX` 单挂载器; 每个 `@keyframes` 配 `prefers-reduced-motion` 降级; atlas/prism/console 对 `shared/fx/` 零引用。
- **HTML 产出**: 一律 dark 主题(深色底 + 浅色字), 样式里必须写 `color-scheme: dark`。

## 主题地图(每节一行, 权威在附件)

- 菜单/入口分层原则 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 菜单/入口分层原则」
- 令牌分工 → [attachments/webui-theme-tokens.md](attachments/webui-theme-tokens.md) 「WEB UI 令牌分工」
- 按钮体系 .bt → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 按钮体系 .bt」
- 弹窗语义配色分级 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 弹窗语义配色分级」
- 四皮肤共用规则族 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI 三皮肤共用规则族」(附件成文时三套, 冻结不追改)
- busy 骨架单点 → [attachments/webui-menu-components.md](attachments/webui-menu-components.md) 「WEB UI busy 骨架单点」
- 悬浮提示 .aq-tip → [attachments/webui-interaction.md](attachments/webui-interaction.md) 「WEB UI 悬浮提示 .aq-tip」
- 选中摘要口径 → [attachments/webui-interaction.md](attachments/webui-interaction.md) 「WEB UI 选中摘要口径」
- fx 动效库与 flux 皮肤 → [attachments/webui-fx.md](attachments/webui-fx.md) 「WEB UI fx 动效库与 flux 皮肤」
- 流量图节拍动效与数值面板 → [attachments/webui-traffic-beat.md](attachments/webui-traffic-beat.md) 「流量图节拍动效」
- HTML 文档 dark 主题 → [attachments/webui-theme-tokens.md](attachments/webui-theme-tokens.md) 「HTML 文档一律 dark 主题」
- 迁移状态展示口径 → 本文件「迁移状态展示口径(路径列)」

## 迁移状态展示口径(路径列)

- **行内两排 A→B 着色**: 状态唯一载体 = 颜色(两排按态着 accent/warn/error, 同为 `currentColor` 且 100% 不透明), 无底形无边框无药丸; **层级靠形状差异: 上排(当前位置)删除线标旧值, 下排(目标位置)常态**(26-11-10 修订 D6: 旧 `opacity:.55` 在深色底 + 高相似路径文本上被读成下排的淡影/伪影, 近视错觉); done/cancelled 回落单排; 判定单点 `decorate.js::relocateView(row)`, 指纹签名同步含 src。pair 模式**替换**单排路径(A 排承载同一值, 原路径行隐藏); **原生 `title` 同步退役**(2026-11-11: 双排时 A/B 已明文 + 悬停浮窗全量, title 只剩单条旧路径反成误导; 单排/one 保留供截断路径看全文, 判定谓词与 sp-body 隐藏同一 `mode !== 'pair'`)。
- **路径 chip 点击筛选(R3 D16, 修订原 D9 零点击)**: A/B 排带 `.f-cell`(cursor+hover)+ 各自独立 `.f-on`, 点击 = `filterFromChip('path', a/b)`(显示值即筛选值, toggle 语义); 仍不开抽屉/链浮窗, 详情走悬停浮窗。
- **路径筛选 = 位置集匹配(R3 D17)**: 匹配与选项计数同一单点 `decorate.js::_pathPositions(r)` —— save_path 恒参与, 进行中三态(moving/pending_finalize/failed)的迁移 src/dst 并入「保存位置」; done/cancelled 历史位置不参与(迁移完成即退出匹配, 既定推论)。消费点四处(filters.js _facetPick/组级谓词/虚拟行谓词 + hr.js _memberPass)禁止各写 save_path 判断。
- **悬停浮窗**: 详情走 `shared/relocate_pop.js`(调度与 hrPop 同参: enter 120ms / leave 160ms / 移入浮窗不关 / teleport body / ESC 退栈); 数据全来自行载荷, 零新请求。
- **皮肤自适应单点**: 状态圆点/端点圆角 = `calc(var(--radius-sm) / 2)` 一条规则四皮肤自适应, 不写皮肤分支; 浮窗「当前位置」行用 `--path-src` 固定色令牌(四皮肤令牌表各定值), 不随状态色。
- **视觉规格单点**: `memory-bank/plans/attachments/relocate-status-display-v2-mockup.html`(四皮肤可切换、交互可点)。
