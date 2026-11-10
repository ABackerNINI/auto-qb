# 双排路径用透明度做层级 = 上排被读成下排的淡影/伪影(近视错觉)

> 摘要: 深色底 + 两排高度相似的路径文本(当前位置/目标位置只差一两级目录)时, 给上排 `opacity:.55` 做「暗/亮」分层, 远看不会被读成层级, 而是被读成下排文字的半透明残影(近视错觉)。层级要靠**形状差异**(删除线/标签), 不能靠亮度差; 尤其别在等宽 11px 路径上用合成斜体(oblique 发虚, 骨架不变, 仍像歪掉的影子)。
> 触发: 双排显示, 保存路径, 整组迁移, relocate, rel-pair, rel-pa, opacity, 颜色浅, 伪影, 重影, 近视错觉, 淡影, 深色底, 层级, 删除线, 斜体, row_lang.css, D6
**Refs:** memory-bank/tasks/26-11-10-webui-relocate-pair-visual.md

### 迁移双排路径(.rel-pa)的透明度分层伪影

- **触发**: 主列表 `save_path` 列在迁移三态(moving/pending_finalize/failed)下渲染行内 A→B 两排(`xtpl-cells.html` 的 `.rel-pair`): 上排 A = `relocate.src`(与原 `save_path` 同一值), 下排 B = `relocate.dst`, 两排同为 11px 等宽、同为 `currentColor` 状态色, 唯一差异是上排 `opacity:.55`。计划 `26-11-07-2344` D6 拍板「当前位置上排(暗)/目标位置下排(亮)」, mockup 与 `conventions/webui.md` 三处一致。用户 2026-11-10 报「上方路径颜色浅, 远看像下方路径的伪影, 像近视错觉」。
- **判别**: 两排文本是否**高度相似**(同源路径树, 只差一两个目录段)且唯一差异是**透明度/亮度**? 是 → 透明度在深色底上只会把上排稀释成背景色, 人眼优先归因于「同一串字印了两遍」而非「层级」。同族陷阱: 等宽字体 `font-style:italic` 多数是合成 oblique, 11px 下字形发虚且骨架不变, 远看仍像歪掉的影子, 不能拿来救场。浮窗「当前位置」用 `--path-src` 固定实色(非透明度)不中招, 别顺手一起改; 四皮肤 CSS 对 `.rel-pa` 无覆盖, 命中面只有 `.rl-scope` 主表。
- **处置**: 上排去掉 `opacity`, 两排同为 100% 不透明状态色; 上排加 `text-decoration: line-through` 标「旧值/即将离开」, 层级载体由亮度差换成形状差异。`row_lang.css` 的 `.rl-scope .rel-pa` 单点改, 同步 `plans/attachments/relocate-status-display-v2-mockup.html` 视觉规格单点(四个状态 `.aq-pa`)与 `conventions/webui.md` 口径; 原计划 D6 行保留作历史、追加 D18 修订行(不篡改已定稿决策)。下排、弧形箭头、tone 着色、rel-pulse、悬停浮窗与四皮肤令牌一律不动。
- **守阵**: `tests/test_webui_relocate_visibility.py::test_p1_pair_upper_row_uses_strikethrough_not_opacity` —— 正则取 `.rl-scope .rel-pa` 规则块, 正反双断言(不得含 `opacity` / 必须含 `text-decoration: line-through`); 红验双验留痕(旧 CSS 反断言红、只去 opacity 未加删除线时正断言红、最终态绿)。最终「远看还像不像伪影」仍按 `cell-frame-vs-text-width.md` 同口径走真机截图目检, 静态断言只防回归。
