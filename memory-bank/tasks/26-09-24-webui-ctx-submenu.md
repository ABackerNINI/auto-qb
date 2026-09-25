# 26-09-24-webui-ctx-submenu — 右键次级菜单: 图标 hover 变灰 / 移出不消失 / 两个"更多"入口

**Status:** Done
**Added:** 2026-09-24
**Updated:** 2026-09-24
**Summary:** 用户报右键次级菜单三条: ①二级菜单图标在鼠标 hover 时变灰; ②二级菜单鼠标移出不消失; ③右键的「复制」二级菜单要移进「更多操作」。根因分别是 ①`.ctx-item:hover .ico` 是**后代**选择器而 `.ctx-sub` 是父项的 DOM 后代 ⇒ hover 父项把整个子面板的图标刷成 `--fg-muted`(且不加 `:where()` 压特异性时, 语义色规则 0,2,0 压不过 hover 的 0,3,0); ②只有 `mouseenter` 展开、没有任何收起路径; ③复制族单列了第二个子面板, 一级出现两个"更多"入口。修法: CSS 改 `.ctx-item:where(:hover) > .ico`(`>` 限直接子级 + `:where()` 压特异性); 收起挂**父项** `mouseleave` 延迟 180ms(`menu.js::scheduleSubClose`/`keepSub`, 延迟只为跨过 4px 缝隙); 复制三项并入「更多操作」末尾。新增静态守阵 1 条 + 冒烟 8 条(双 UI × 四条), **已对 HEAD 红验**(回退棱镜两处 ⇒ CTX-04/CTX-05 变红)。实测: 全量 1375 passed + 1 skipped(另有 2 条 GBK 守阵因本 shell `PYTHONUTF8=1` 恒红, 非代码缺陷) / 冒烟 92 项 0 失败。
**Topics:** webui-ctx-submenu

## 原始请求

> 修复问题: * WEBUI右键二级菜单图标在鼠标hover在菜单上时变灰, 同时二级菜单在鼠标移出时不会消失
> * 将鼠标右键复制二级菜单移入更多操作

## 思考过程与决策

### ① 变灰不是"配色选错", 是**选择器作用域 + 特异性**两层叠加

肉眼症状是"hover 时图标灰了", 但改色值没有意义 —— 实际有两处成因, 各修一半都不够:

- **作用域**: `.ctx-item:hover .ico` 命中"被 hover 的 `.ctx-item` 的**全部后代** `.ico`"。
  而子面板是父项的 DOM 后代(`.ctx-item.has-sub > .ctx-sub > .ctx-item`), 于是 hover「更多操作」
  时**整个子面板**的图标一起被刷成 `--fg-muted`。→ 必须 `>` 限到直接子级。
- **特异性**: 只加 `>` 仍不够 —— `.ctx-item:hover > .ico` 是 0,3,0, 而语义色规则
  `.ctx-item .ico-queue` 只有 0,2,0 ⇒ hover 照样压过语义色, 有色图标还是变灰。
  → 用 `:where(:hover)` 把 `:hover` 的特异性压成 0(整条 0,2,0), 与语义色规则同重,
  再靠**源码顺序**让位(语义色规则在其后)。这与 `colAlignCss` 用 `:where()` 压特异性是同一招。

判据落在"色值"而不是截图: 悬停父项时读 `.ctx-sub .ico-queue` 的 computed color,
必须等于 `var(--teal)` 且不等于 `var(--fg-muted)`(见冒烟 CTX-04)。

### ② 收起只能挂**父项**, 而且必须延迟

- 挂父项: `mouseleave` 只在"指针离开该元素**及其全部后代**"时触发 ⇒ 父项 → 面板 / 面板 → 父项
  都不触发(面板是后代), 面板自身只需要 `@mouseenter="keepSub()"` 撤销挂起的收起。
  反过来**在面板上也挂 mouseleave 是错的**: 从面板回到父项时它会立刻排一次收起,
  而父项不会再收一次 `mouseenter` ⇒ 180ms 后"明明鼠标在入口上, 面板却自己关了"。
- 延迟 180ms(`SUB_CLOSE_DELAY_MS`): `.ctx-sub` 的 `left: calc(100% + 4px)` 在父项与面板之间
  留了 4px 缝隙, 同步收起会在过缝瞬间关掉面板 ⇒ 表现为"鼠标根本进不去子面板"。
- 一级菜单关闭(`menu.visible` watch)与点击收合(`toggleSub`)都要 `keepSub()` 撤销挂起的定时器。

### ③ 合并入口的判据: "低频动作归堆, 不新开入口"

`conventions/webui.md` 的原则是"菜单项数增长时先问能否归入既有次级菜单"。复制族此前单列
第二个子面板, 使一级出现两个"更多"入口 —— 用户每次都得先选"该进哪个"。合并后一级只有一个
`has-sub`, 复制三项放在「更多操作」末尾(队列族 / 开关族 / 复制族 三段, 中间各一条分隔线)。

## 实现计划

1. **① 变灰**: 两套 UI 的 `.ctx-item:hover .ico` → `.ctx-item:where(:hover) > .ico`(作用域 + 特异性两层一起改)。
2. **② 收起**: `menu.js` 加 `keepSub()` / `scheduleSubClose()` + `SUB_CLOSE_DELAY_MS`; 父项挂
   `mouseleave`、面板挂 `mouseenter`; `app.js` 加 `_subCloseTimer` 并在 `menu.visible` 关闭 / `toggleSub`
   收合时撤销挂起的定时器。
3. **③ 合并**: 删「复制」子面板, 三项复制并入「更多操作」末尾(分隔线分段); 双 UI 逐项一致。
4. **守阵**: 静态守阵 1 条(`test_web.py`) + 冒烟 8 条(双 UI × 四), 并对 HEAD 红验。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | CSS hover 规则(双 UI 成对改) | ✅ |
| 2 | 移出延迟收起(menu.js + app.js + 双模板) | ✅ |
| 3 | 复制族并入「更多操作」, 一级只留一个入口 | ✅ |
| 4 | 静态守阵 + 冒烟 8 条 + 红验 | ✅ |

## 进度日志

- 2026-09-24 23:0x —— 三条一次修完(6 个源文件); 全量 1375 passed + 1 skipped
  (GBK 两条因本 shell `PYTHONUTF8=1` 恒红, 非代码缺陷); 冒烟 92 项 0 失败(单 UI 各 46);
  红验: 回退棱镜 CSS + 父项 `mouseleave` ⇒ CTX-04/CTX-05 变红, 已恢复。

## 改动

| 文件 | 改动 |
|---|---|
| `shared/menu.js` | `openSub` 先撤销挂起的收起; 新增 `keepSub()` / `scheduleSubClose()` 与常量 `SUB_CLOSE_DELAY_MS = 180`; `toggleSub` 收合时也撤销; 顶部注释写清两条"为什么" |
| `shared/app.js` | data 新增 `_subCloseTimer: 0`;`menu.visible` 关闭时 `keepSub()` 再复位 `subMenu`; `subMenu` 取值注释收敛为 `"" \| "advanced"` |
| `atlas/index.html` · `prism/index.html` | 「更多操作」父项加 `@mouseleave="scheduleSubClose()"`, 子面板加 `@mouseenter="keepSub()"`; 删除「复制」子面板, 三项复制并入「更多操作」末尾 |
| `atlas/style.css` · `prism/css/components.css` | `.ctx-item:hover .ico` → `.ctx-item:where(:hover) > .ico`(两处 UI 成对改) |
| `tests/test_web.py` | 新增 `test_frontend_ctx_submenu_single_entry_and_hover_close`(静态守阵: hover 规则写法 / 一级只有一个入口 / 复制三项在面板内 / 两个方法与延迟存在 / 关闭时撤销定时器) |
| `scripts/ui_smoke.cjs` | 新增 CTX-04 / CTX-05 / CTX-06 共 8 条(双 UI × 四条) |

## 实测

- 全量 `commands run test.full`: **1375 passed + 1 skipped** / TOTAL 91%(9278 / 727 / 3128 / 277) /
  sidefx 越界 0。⚠ 另有 2 条 `test_commands_engine.py` GBK 守阵失败 —— **非代码缺陷**: 本工具 shell 带
  `PYTHONUTF8=1` + `LC_ALL=C.UTF-8` ⇒ `locale.getpreferredencoding(False)` 返回 utf-8, `_decode` 的
  GBK 回退不可达(上一轮切片已记同一结论, `env -u PYTHONUTF8` 后全绿)。
- 冒烟(桩 3000 种子, `--ui both`): **92 项 0 失败**(单 UI 各 46; 新增 8 条全过)。
  其中一次双 UI 轮里 `[prism] P0-3 剧行乐观` 抖动失败一次(轮询 1.5s 内未出现), 单 UI 重跑 46/0 ⇒ 时序抖动。
- **红验**: 临时把棱镜改回 `.ctx-item:hover .ico` 并摘掉父项 `mouseleave` ⇒
  `CTX-04 图标 rgb(82,112,140)(= --fg-muted)` / `CTX-05 残留 .ctx-sub 1 个` 双双变红; 验完已恢复。

## 单点指针

- 判据 → [../pitfalls/web-ui/overlays.md](../pitfalls/web-ui/overlays.md)(条目「flyout 次级菜单」)
- 分层原则 → [../conventions/webui.md](../conventions/webui.md)(CTX-06: 一级只允许一个次级菜单入口)
- 测试数字 → [../testing/baseline.md](../testing/baseline.md) · 冒烟规模 → [../testing/smoke.md](../testing/smoke.md)
- 上一轮(CTX-03) → [26-09-24-webui-ctx-menu-multi-select.md](26-09-24-webui-ctx-menu-multi-select.md)
