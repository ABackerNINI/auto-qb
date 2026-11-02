# Spec: flux 皮肤浮动层不透明兜底（毛玻璃失效修复）

> 状态: 待批准 | 骨架: 本任务 spec/tasks | 范围: 仅 WEBUI 样式层, 不改后端/模板/JS

## 1. 结论(根因)

flux 是四皮肤里**唯一**把层级底 token 写成半透明的皮肤:

- `--bg-card: rgba(24, 35, 52, .82)` (透 18%)
- `--bg-elev: rgba(30, 44, 66, .92)` (透 8%)

flux 的 glass 语言允许页底透过卡片/行形成"层叠玻璃", 并且**只给 4 个常驻大面**挂真毛玻璃(`.topbar` / `.statusbar` / `.drawer` / `.modal`, `backdrop-filter` 预算由 `tests/test_webui_static_skins.py::_FLUX_BACKDROP_BUDGET = 4` 钉死)。其余浮动层没有 `backdrop-filter`, 却沿用上面两个半透明 token 作底 —— 下方正文直接透出, alpha 越低越明显:

- `.ctx-menu` / `.ctx-sub` / `.hr-pop` / `.hp-arrow` 用 `.82` → 右键菜单、HR 悬停卡透得最明显;
- `.pop-menu` / `.col-menu` 用 `.92` → 语言/皮肤下拉、列选择器轻微透字;
- `.speed-pop` 渐变 + `.82` → 限速浮层透字。

此前修好的两处之所以正常: `.drawer`(详情面板)与 `.modal`(添加种子窗口)各挂 `backdrop-filter: blur(14px)`, 半透明底被磨砂化, 不呈现可读正文。

## 2. 修复策略(单点, 一次覆盖全部同类)

**不新增 `backdrop-filter`**(会突破守阵预算 4、且 PERF-01 禁止嵌套模糊)。改为新增一个**浮层不透明表面令牌** `--bg-pop`, 等价于 `--bg-elev` 叠在页底 `--bg` 上的合成色 `#1c2a3f`, 供所有"无毛玻璃的浮动层"作不透明兜底。

不直接把 flux 的 `--bg-elev` 改成不透明: 它同时喂 `.modal`/`.toast` 的 `--msg-surface`、`select option`、`.hb-pill`、`.pop-mgr-btn` 等, 全局改值会抹掉弹窗的磨砂观感与卡片玻璃语言; 也不改 `--bg-card`(卡片/行玻璃层叠的设计本体)。

### 令牌落点
| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/flux/style.css` | `:root` 增 `--bg-pop: #1c2a3f;`（注释说明= `--bg-elev(.92)` 覆在 `--bg` 上的不透明等效, 仅用于无毛玻璃浮层) |
| `src/auto_qb/webui/static/atlas/style.css` | 增 `--bg-pop: var(--bg-elev);`（惰性, 零视觉变化, 满足名集守阵） |
| `src/auto_qb/webui/static/console/style.css` | 同上 |
| `src/auto_qb/webui/static/prism/css/tokens.css` | 同上（主题内 `--bg-elev` 已按主题取值, 惰性） |

> 守阵 `test_frontend_skin_css_token_parity` 要求四皮肤令牌名集相等, 故四file 同轮补名。

### flux 自有浮层(就地换 token)
| 文件 | 选择器 | 现值 → 新值 |
|---|---|---|
| `flux/css/components.css` | `.col-menu, .pop-menu` | `--bg-elev` → `--bg-pop` |
| `flux/css/components.css` | `.ctx-menu` | `--bg-card` → `--bg-pop` |
| `flux/css/components.css` | `.ctx-sub` | `--bg-card` → `--bg-pop` |
| `flux/css/components.css` | `.ce-chart-tip` | `--bg-elev` → `--bg-pop` |
| `flux/css/dialogs.css` | `.speed-pop` | 渐变基色 `--bg-card` → `--bg-pop`（保留渐变/切角） |
| `flux/css/dialogs.css` | `.hr-pop` | `--bg-card` → `--bg-pop` |
| `flux/css/dialogs.css` | `.hp-arrow` | `--bg-card` → `--bg-pop`（必须与卡体同色） |
| `flux/css/dialogs.css` | `.hr-full-modal` | 渐变基色 `--bg-card` → `--bg-pop`（有遮罩但无毛玻璃, 大面板可读性优先） |
| `flux/css/dialogs.css` | `.add-drop-box` | 渐变基色 `--bg-elev` → `--bg-pop` |
| `flux/css/views.css` | `.hist-tip` | `--bg-elev` → `--bg-pop` |
| `flux/css/views.css` | `.col-ghost` | `--bg-elev` → `--bg-pop` |

> components.css 已 700 行顶格: 以上全是**取值替换**, 不增行; dialogs.css/views.css 增行后仍 ≤700。

### shared 共用浮层(仅 flux 作用域覆盖)
落点: `flux/css/dialogs.css` 末尾新增一段（`html[data-fx-preset]` 前缀提权, 胜过后加载的 `shared/console_hub.css` 的 0,1,0 规则）:

`.hb-pop`（用 `background-color`, 保留其 `background-image` 渐变）、`.hb-pop-arrow`、`.hb-tr-drop`、`.search-help-pop`、`.aq-tip`、`.err-panel`、`.rowlang-menu`（行语言菜单, 定义在 `shared/row_lang.css`, flux 侧覆盖）。

不改 `shared/console_hub.css` / `shared/row_lang.css` 本体 —— 那是四皮肤共用层, 改值会波及 atlas/prism/console。

## 3. 核对清单(逐一确认)

| 浮动层 | 现状 | 处理 |
|---|---|---|
| 语言/皮肤下拉 `.pop-menu` | `--bg-elev` 无 blur | 改 |
| 行语言菜单 `.rowlang-menu` | `--bg-elev` 无 blur | flux 侧覆盖 |
| 列选择器 `.col-menu` | `--bg-elev` 无 blur | 改 |
| 右键菜单 `.ctx-menu` / `.ctx-sub` | `--bg-card` 无 blur | 改 |
| 限速浮层 `.speed-pop` | 渐变+`--bg-card` 无 blur | 改 |
| HR 悬停卡 `.hr-pop`/`.hp-arrow` | `--bg-card` 无 blur | 改 |
| 设置页图表悬停 `.ce-chart-tip` | `--bg-elev` 无 blur | 改 |
| 下载/限速历史图悬停 `.hist-tip` | `--bg-elev` 无 blur | 改 |
| 列头拖动虚影 `.col-ghost` | `--bg-elev` 无 blur | 改 |
| 拖放落点 `.add-drop-box` | 渐变+`--bg-elev`, 有 `.62` 遮罩 | 改 |
| HR 全屏覆盖 `.hr-full-modal` | 渐变+`--bg-card`, 有 `.72` 遮罩无 blur | 改 |
| 设置页就近说明 `.hb-pop`/`-arrow` | `--bg-elev` 无 blur | flux 侧覆盖 |
| 站点/规则集命中 `.hb-tr-drop` | `--bg-elev` 无 blur | flux 侧覆盖 |
| 搜索语法卡 `.search-help-pop` | `--bg-elev` 无 blur | flux 侧覆盖 |
| 全局 title 浮层 `.aq-tip` | `--bg-elev` 无 blur | flux 侧覆盖 |
| 通知面板 `.err-panel` | `--bg-elev` 无 blur | flux 侧覆盖 |
| `.drawer` 详情面板 | `--bg-card` + blur(14) | 不改(已正常) |
| `.modal` 添加种子窗 | `--msg-surface` + blur(14) | 不改(已正常) |
| `.topbar` / `.statusbar` | 半透明 + blur(12) | 不改(预算内) |
| `.toast` 通知条 | `--msg-surface(.92)` 无 blur, 刻意过路小条 | 不改(`--msg-surface` 单点约束) |
| `.modal-mask` / `.hr-full-mask` / `.add-drop-mask` | 半透明遮罩, 禁 blur | 不改(PERF-01) |
| `select option` / `.hb-pill` / `.pop-mgr-btn` | 非浮动层 | 不改 |
| `.theme-menu` | prism 专属 | 不适用 |

余项(实现前用一次 grep 收口): `.login-mask` 及 flux 内其余 `position: fixed|absolute` + `--bg-*` 组合, 确认无漏; 若有则同规则纳入。

## 4. 验证

1. `commands run test.quick`（或定向 `tests/test_webui_static_skins.py`）:
   - `_scan_backdrop_filter`: flux 声明数仍 = 4, 五类禁用元素零命中;
   - 单 CSS ≤700 行;
   - `test_frontend_skin_css_token_parity` 四皮肤名集相等。
2. 静态自查: 全站 grep 确认无残留"浮动层 + 半透明 bg + 无 blur"组合。
3. 真机/浏览器: 需在 flux 皮肤下逐项打开（语言/皮肤下拉、列选择器、右键菜单、限速浮层、HR 悬停卡、搜索语法卡、通知面板、设置页就近说明、拖放提示）确认无透字; 本机 Playwright 为软渲染, 仅作功能核对, 不作性能结论。

## 5. 不做

- 不 commit / 不 push（未授权）。
- 不改 JS/模板/后端; 不改 shared 共用 CSS 本体; 不给任何浮层新增 `backdrop-filter`。
- 计划外缺陷只记录, 不顺手修。
