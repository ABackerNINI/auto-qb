# 设置页重构 · 模板挑选

> 目的: 「第 N 次重构」之前先把版式定下来。四套模板**完全不沿用旧版式** —— 导航模型、
> 字段排版、说明文字的落点都不一样。挑一套再动 `src/auto_qb/web_ui/` 的代码。

## 怎么挑

1. 双击打开 **[index.html](index.html)** —— 挑选页: 现状诊断、四套实页预览（可切主题）、横向对比表、文案改写对照。
2. 点「打开实页」进单套模板, 在页面里点导航、Tab 切焦点、切主题, 交互都是能用的。
3. 挑定后回来说一声, 再按选定方案正式改造。

## 目录

| 文件 | 说明 |
|---|---|
| `index.html` | 挑选页（诊断 + 五套预览 + 对比表 + 文案对照） |
| `05-console-hub.html` | **A+C+D 组合** — A 的视觉 + C 的布局（首页卡片 → 二级页）+ D 的说明改成就近浮窗；带「Ash Thorp 原色」皮肤开关 |
| `05-console-hub.md` | **本方案的设计说明书**：设计决定 + 发光/语调系统的完整 CSS + **9 条踩过的坑**（尤其 CSS 变量"固化"那条）+ 文案改写对照 + 落地到 `src/auto_qb/` 的文件清单与验收清单。**正式改造代码前先读它。** |
| `01-console-hud.html` | **A · 仪表台 Console** — 左侧 rail + 机械切角 + 等宽读数 + 分段 LED；带「Ash Thorp 原色」皮肤开关 |
| `02-editorial-flow.html` | **B · 文档式 Editorial** — 顶部标签 + 标签在上/控件在下 + 说明当正文写 + 手风琴 |
| `03-hub-spoke.html` | **C · 卡片总览 Hub & Spoke** — 首页状态卡片网格 + 搜索, 点进二级页 |
| `04-split-explain.html` | **D · 双栏说明 Split Explain** — 极紧凑行 + 右侧常驻说明栏 |
| `_shared/theme-tokens.css` | 真实 WEB UI 的颜色/结构令牌（生成物, 勿手改） |
| `_shared/demo.css` | 四套共用的演示条与表单元件（开关/输入/按钮/徽章） |

## 关于主题

四套模板一律引用 `_shared/theme-tokens.css` 里的令牌, **不写死色值** —— 因为线上 WEB UI 有 5 套主题
（深海机房 / 暗夜星云 / 极地晨霜 / 麦秋 / 品牌轨道, 其中 2 套亮色）。切主题时模板跟着变,
不会出现「只在深色下好看」这种以前反复踩的坑。

`_shared/theme-tokens.css` 是由真实主题文件拼接生成的, 改了 `src/…/prism/css/themes/*.css` 之后重跑:

```bash
python - <<'PY'
from pathlib import Path
root = Path("src/auto_qb/web_ui/static/prism/css")
parts = ["/* 生成物, 勿手改 */\n", (root / "tokens.css").read_text(encoding="utf-8")]
for t in sorted((root / "themes").glob("*.css")):
    parts += ["\n/* ---- %s ---- */\n" % t.stem, t.read_text(encoding="utf-8")]
Path("resources/settings-page-templates/_shared/theme-tokens.css").write_text("".join(parts), encoding="utf-8")
PY
```

**Ash Thorp** 不是主题, 是 A 方案里一个可切的原色皮肤（`html[data-skin="ash"]` 覆盖同一批令牌）。
要不要真的做成第 6 套主题（`css/themes/ash.css` + `js/theme.js` 加一行）是独立决定, 不影响选版式。

## 挑选后正式改造的落点

| 改动 | 文件 |
|---|---|
| 设置页模板（两套 UI 各一份, 目前是复制关系） | `src/auto_qb/web_ui/static/prism/index.html`、`static/atlas/index.html` |
| 字段渲染组件 | `static/shared/config_editor.js` + `index.html` 里的 `<script id="tpl-ce-field">` |
| 设置页样式 | `static/prism/css/views.css`（`.ce-*` 段）、`static/atlas/style.css` |
| **分组/字段文案**（本轮最大的内容改动） | `src/auto_qb/config/schema/groups.py`（`Group(...)` 的 help、`Field(...)` 的 help/risk）+ `schema/trackers.py`、`schema/rules.py` |
| 新增 schema 字段（D 方案需要: 默认值/何时改/易混淆项） | `src/auto_qb/config/schema/fields.py` + `config/validation`（新键必须进 `validate_config`） |

文案改写对照见 `index.html` 末尾那张表 —— 左列是现在线上在用的说法, 右列是模板里已经落地的成品文案,
挑完版式可以直接搬进 schema。
