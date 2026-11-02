# 26-11-02-webui-flux-overlay-opacity — 修复 flux 皮肤浮层透出正文

**Status:** Done
**Added:** 2026-11-02
**Updated:** 2026-11-02
**Summary:** flux 皮肤独有半透明表面令牌 + 无 blur 浮层 ⇒ 透出正文; 新增 --bg-pop 不透明兜底并覆盖 19 处浮层
**Topics:** webui-flux-overlay-opacity
**Refs:** memory-bank/activeContext/26-11-02-2033-webui-flux-overlay-opacity.md

## 原始请求

1. 修复 flux 皮肤下浮动层背景透明/毛玻璃失效: 语言/皮肤选择下拉框、限速修改弹窗、HR 悬停卡、右键菜单等能透出下方正文。
2. 不只修点名的几处 —— WEBUI 所有窗口/弹窗/下拉/菜单/悬停卡在 flux 下逐一核对, 同根因统一修。

## 思考过程与决策

- **根因不在 blur, 在令牌**: 四皮肤里只有 flux 把 `--bg-card` 写成 `rgba(...,.82)`、`--bg-elev` 写成 `rgba(...,.92)`;
  另三皮肤两 token 都是不透明 hex。flux 毛玻璃预算钉死 4 处(顶栏/状态栏/抽屉/弹窗), 其余浮层没有 `backdrop-filter`
  ⇒ 半透明底直接把下方正文透上来。已修过的详情面板/添加种子窗口正常, 正因为它们挂 blur。
- **取舍**: 不给浮层补 `backdrop-filter`(预算守阵 `_FLUX_BACKDROP_BUDGET = 4` 会红, 且大面模糊有性能成本), 也不把
  `--bg-card/--bg-elev` 全局改成不透明(会破坏 glass 皮肤的层叠语言)。改加一个**只给无毛玻璃浮层**的不透明令牌
  `--bg-pop` = `--bg-elev(.92)` 覆在页底 `--bg` 上的等效色(flux `#1c2a3f`)。
- **四皮肤令牌名集相等**: 另三皮肤补 `--bg-pop: var(--bg-elev)` 惰性别名(零视觉变化), 否则
  `test_frontend_skin_css_token_parity` 红。
- **shared 层不动本体**: `console_hub.css` / `row_lang.css` 为四皮肤共用, 它们读 `--bg-elev`; 只在 flux 侧用
  `html[data-fx-preset]` 前缀覆盖底色(特异性 0,2,1 > shared 的 0,1,0, 且级联序在 shared 之后也生效)。
- **体量约束**: `flux/css/components.css` 已恰好 700 行(硬上限), 本文件只原地换值不增行。

## 实现计划

1. flux `style.css` 新增 `--bg-pop: #1c2a3f`; atlas/console `style.css` 与 prism `tokens.css` 补惰性别名。
2. flux `components.css`: `.col-menu/.pop-menu`、`.ctx-menu`、`.ctx-sub`、`.ce-chart-tip` 换 `--bg-pop`。
3. flux `dialogs.css`: `.hr-full-modal`、`.add-drop-box`、`.speed-pop`、`.hr-pop`、`.hp-arrow` 换 `--bg-pop`;
   文末追加 shared 浮层覆盖块(`.hb-pop` 用 `background-color` 保留原渐变)。
4. flux `views.css`: `.hist-tip`、`.col-ghost` 换 `--bg-pop`。
5. 验证: `test.quick` 全绿; flux `backdrop-filter` 仍恰 4 处; CSS 单文件 ≤700 行; `--bg-pop` 声明 4 处。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| T1 | 新增 `--bg-pop` 令牌(flux + 三皮肤补名) | Done(2026-11-02) |
| T2 | `components.css` 四个浮层换 `--bg-pop` | Done(2026-11-02) |
| T3 | `dialogs.css` 五个浮层换 `--bg-pop` + shared 覆盖块 | Done(2026-11-02) |
| T4 | `views.css` 两处浮层换 `--bg-pop` | Done(2026-11-02) |
| T5 | shared 浮层 flux 作用域覆盖(7 处) | Done(2026-11-02) |
| T6 | 收口 grep 与 login-mask 核查 | Done(2026-11-02) |
| T7 | `test.quick` 与静态守卫 | Done(2026-11-02) |

## 进度日志

### R0 · 立档 (2026-11-02)

统一根因修复完成: flux 自有 12 处浮层 + shared 7 处覆盖 = 19 处; 全量测试通过(数字见 kb.baseline),
flux `backdrop-filter` 仍恰 4 处, 三 CSS 文件行数均达标。口径已回写 `conventions/webui.md` 与
`pitfalls/web-ui/overlays.md`。

- 2026-11-02 20:33 新增 --bg-pop 不透明浮层底: flux 自有 12 处浮层换值 + shared 7 处 html[data-fx-preset] 覆盖, 另三皮肤补惰性别名; 根因=flux 表面令牌带 alpha 且毛玻璃预算仅 4 处; 口径回写 webui.md 与 overlays.md
