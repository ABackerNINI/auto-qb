# 26-10-29-webui-move-dialog-pick-geometry — 设定位置对话框二修: 点选只回填 + 几何基线/过渡

**Status:** Done
**Added:** 2026-10-29
**Updated:** 2026-10-29
**Summary:** 「设定位置」对话框二修: 点选候选只回填(移动只由按钮/手输回车发起), 收层态基线 243→360px, 开层预留从 0↔272 硬切改为 200ms 过渡, 打开不再自动展开下拉。
**Topics:** webui-move-dialog-pick-geometry
**Refs:** memory-bank/plans/26-10-29-0041-plan-webui-move-dialog-pick-geometry.html, memory-bank/pitfalls/web-ui/dialog-geometry-jump.md

## 原始请求

1. 「WEBUI 种子设定位置窗口点击下拉框中的选项就触发移动, 需要改成点击『设定位置』按钮后移动」
2. 「WEBUI 种子设定位置窗口太小, 点击下拉框高度跳变」
3. grilling 定稿后的补充口径: 「Q5 窗口再大气一点 / Q6 设计要简洁明了, 明显的交互逻辑不必写 / Q7 不自动展开」+「另外窗口不能『跳变』, 要用动画自然过渡」

## 思考过程与决策

计划全文与 D1–D7 拍板见 `memory-bank/plans/26-10-29-0041-plan-webui-move-dialog-pick-geometry.html`。要点:

- 两条报障同源: ①`moveApplyPath` 回填后直调 `submitMoveDialog`(点选即移动); ②19 日首修为「开层时给 body 预留 272px」, 条件类一切换 = 高度 ±272px 硬跳, 收层态又是 243px 小个子。
- 三条硬取舍:
  1. **点选只回填, 手输回车仍提交** —— 回车是明确确认手势, 不该逼用户再挪鼠标; 用 `comboKeydown` 的可选 `ctx.onEnter` 钩子分开两条路, 其余四个下拉不传(零变化)。
  2. **不选「高度恒定 + 常驻预留」** —— 打开不自动展开后, 恒定高会在第一眼露出 ~270px 空箱, 而用户要求不写说明文案填它; 改「基线抬升 + padding 过渡」, 大气/不跳/有动画三条同时满足。
  3. **body 不能 `flex:1`** —— 全局 `* { box-sizing: border-box }`, padding 会长在固定高度里, 内容反被挤成滚动条; 高度增长只能靠 body 的 auto 高度随 padding 走, 动作条用 `margin-top:auto` 钉底。
- 实施时纠正初稿一处: 面板入场**不需要**新增 `.pop-enter-*` 规则 —— `.pop-menu` 自带 `animation: drop-in .12s`, 再加 transition 是死规则且与动画争同一组属性。

## 实现计划

1. **S1 行为收口**: `moveApplyPath` 去提交; `openMoveDialog` 置 `moveSuppressOpen`; `openMovePathMenu` 首行消费 + 触发 settle; 模板按钮空态置灰。
2. **S2 共享单点**: `comboKeydown` 回退分支 `(ctx.onEnter || ctx.onPick)(v)` + 头注 ctx 清单补一行。
3. **S3 几何**: 三皮肤成对(基线 min-height 360 / 动作条钉底 / padding 200ms 过渡 / reduced-motion 关) + `MOVE_POP_SETTLE_MS=240` 与 `_movePopSettle`。
4. **S4 守阵**: 静态 8 条新断言(点选不提交 / onEnter / 置灰 / 抑制标志 / settle 常量 / 三皮肤 CSS)。
5. **S5 e2e**: 收层态基线 + ResizeObserver 过渡采样 + Esc 回落 + 点选零写请求 + 按钮一次写请求。
6. **S6 收尾**: 全量测试 → 基线切片 → 坑档 → 回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 行为收口(点选只回填 / 不自动展开 / 空态置灰) | Done(2026-10-29) |
| S2 | `comboKeydown` 加 `ctx.onEnter` 钩子 | Done(2026-10-29) |
| S3 | 三皮肤几何: 基线 360 + padding 过渡 + settle 重测 | Done(2026-10-29) |
| S4 | 静态守阵改写 + 扩容 | Done(2026-10-29) |
| S5 | e2e 重写(几何/过渡/点选不移动) | Done(2026-10-29) |
| S6 | 全量测试 + 基线切片 + 坑档 + 回写 | Done(2026-10-29) |

## 进度日志

### R0 · 立档 (2026-10-29)

六步全部落地。几何实测: 收层态 H0 = 360、开层终值 H1 = 515(prism)/513(atlas), ResizeObserver 抓到 12 帧、其中 6 帧落在中间 → 高度确为过渡; 列表 210px 未被限高截断; 下拉底缘在 body 客户区内(-12px)。e2e 双皮肤全绿; 全量测试零失败, 覆盖率门槛达标(数字见基线切片 `26-10-29-0053`, 按口径不在此手抄)。坑档新增 `pitfalls/web-ui/dialog-geometry-jump.md`(条件类切高度必须带 transition + 过渡期量净空必重测)。

- 2026-10-29 01:07 设定位置对话框二修: 点选只回填/基线 360/200ms 过渡/不自动展开; e2e 双皮肤全绿, 全量零失败
