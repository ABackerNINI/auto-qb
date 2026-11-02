# 26-11-03-webui-ctx-src-target-marker — 右键目标行持续可见标识：四皮肤 .ctx-src 改静态实心 outline 框

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 右键目标行持续可见标识：四皮肤 `.ctx-src` 改静态实心 outline 框，绕过 row_lang flat 对 box-shadow 的归零与左条/选中条同色混淆；新增四皮肤同值静态守阵与全量基线切片
**Topics:** webui-ctx-src-target-marker
**Refs:** memory-bank/testing/baselines/26-11-03-0032-ctx-src-target-marker.md, memory-bank/pitfalls/web-ui/row-shadow-zeroed-by-rowlang.md

## 原始请求

1. 定位现状: 右键种子行时的强调动效是什么(CSS 动画/类名/时长), `.ctx-src` 在菜单开/关时如何存续, 关闭后是否零标识。
2. 按既有口径给持续可见标识方案: 参考 `conventions/webui-scope.md` 三态(选中 / 键盘光标 / 触发锚点)、`pitfalls/web-ui/overlays.md`、`conventions/webui.md` 配色与 dark 约定; 不能与选中底色、`.kb-cursor` 虚线混淆, 要一眼看出"这是右键目标行"。
3. 最小实现, prism/atlas 两皮肤一致; 不改选区/锚点语义(上一轮结论: 不写 `selAnchor*`)。
4. 起干净端口桩实测截图, 补/跑 `.ctx-src` 静态守阵; 菜单开、关两态都要可辨。
5. 不 commit/push, 不改无关代码; 设计文档与现状冲突时以文档为准并说明取舍。其后用户追加指令: 提交(commit+push)。

## 思考过程与决策

- 动效取证: 唯一与 `.ctx-src` 绑定的动画是 flux 的 `fx-row-flash` 600ms(`html[data-fx-preset]` 域); prism/atlas/console 的 `animationName` 实测为 `none`。
- "动效消失后没有标识"的真因不是动效太短, 而是**静态规则失效/不可辨**: atlas 里旧规则 `box-shadow: inset 2px 0 0 var(--accent), inset 0 0 0 1px var(--accent-line)` 被 `shared/row_lang.css` 的 flat 行语言 `html[data-rowlang]... .rl-scope .group-row { box-shadow: none }`(特异性远高)归零, 计算值恒 `none`; 且左条与 `.group-row.selected::before` 选中条同几何同色, 生效也会被读成"已选中"。
- 拍板: 用 `outline: 2px solid var(--accent); outline-offset: -2px` —— 不参与 box-shadow 级联、不铺底色、不用左条; 实心 2px 与 `.kb-cursor` 的 1px 虚线按线型可分。四皮肤逐条同值(用户点名 prism/atlas, 另两皮肤防漂移)。
- 关闭菜单仍清除标记: 遵循 CTX-02 与 overlays.md「触发源强调只在菜单打开期」, 不新增常驻状态; 若需"关后仍常驻"要另立 `lastCtxTarget`, 属文档改口径, 本轮不做。
- 未动共享 JS, 未写 `selAnchor*`/`kbCursor`, 未改选区/焦点语义。
- 取舍: 样式注释一度把 atlas/flux 的 `components.css` 顶到 701/708 行, 触发 700 行体量守阵, 已精简注释回到上限内。

## 实现计划

1. 走查动效与 `.ctx-src` 生命周期(menu.js / flux fx-mount / overlays.md)。
2. 四皮肤 `components.css` 行级 `.ctx-src` 规则替换为静态实心 outline 框。
3. 新增 `test_frontend_ctx_src_target_marker_parity` 静态守阵(四皮肤四行类 + 禁 box-shadow/左条/底色/动画 + 同值)。
4. 8161 新桩 Playwright 四皮肤实测(菜单开/关 + 计算值 + 截图)。
5. `commands run test.full` 闸门。
6. 收尾 DoD 回写 + `ship.commit`。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 动效与 `.ctx-src` 生命周期取证 | Done(2026-11-03) |
| 2 | 四皮肤 `.ctx-src` 静态 outline 框落地 | Done(2026-11-03) |
| 3 | 静态守阵新增并跑通 | Done(2026-11-03) |
| 4 | 8161 桩四皮肤实测(开/关 + 截图) | Done(2026-11-03) |
| 5 | `test.full` 闸门 | Done(2026-11-03) |
| 6 | DoD 回写与提交 | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

完成取证、四皮肤实现、静态守阵与真机实测: 菜单打开 1.2s 后四皮肤 `.ctx-src` 计算值均为实心 2px accent outline(offset -2px), `.kb-cursor` 仍为 1px 虚线; 菜单关闭后 `.ctx-src` 计数归零(按 CTX-02 口径)。全量测试数字见最新基线切片, 不在本档案手抄。

- 2026-11-03 00:33 右键目标行标识改四皮肤静态实心 outline 框(绕过 row_lang box-shadow 归零/左条与选中条同色), 新增静态守阵与基线切片
