# 26-11-11-webui-flux-chip-hover-glow — flux 三种筛选 chip hover 辉光统一: site-chip 形状分层

**Status:** Done
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** flux 站点 chip 形状分层修三种筛选 chip hover 辉光被切角裁掉: clip-path 挪 ::before 切角绘制层、本体辉光四边闭合, 静态守阵 + flux 显式 e2e 双验, 状态边线随目检迁入 ::before
**Topics:** webui-flux-chip-hover-glow
**Refs:** memory-bank/plans/26-11-10-0921-plan-flux-chip-hover-glow.html, memory-bank/pitfalls/web-ui/clip-path-clips-outer-glow.md, memory-bank/testing/baselines/26-11-11-0314-flux-chip-hover-glow.md

## 本篇只回答

flux 三种筛选 chip 的 hover 辉光为什么会被控件层切角裁掉、site-chip「形状与辉光分层」怎么落(本体与 ::before 各画什么)、守阵与 e2e 怎么钉形态、W1-3 预留路径何时被触发、还剩什么没做。方案与取舍的单点在计划档案(Refs), 本篇不复述。

## 原始请求

1. 用户立项实施计划 26-11-10-0921(flux 三种筛选 chip hover 辉光统一; 仅 flux 皮肤 / 零 components.css 改动 / fx-mount.css 唯一落点), 按 W1-W3 分期实施。
2. 实施完成与用户真机目检全过后, 按收尾 DoD 归档(本档案)。

## 思考过程与决策

- **根因**(计划 R0 收录): `.site-chip` 本体挂 `clip-path` 切角, 控件层 clip-path 连带裁掉 box-shadow 外发光 —— 辉光只显一侧/两侧, 与另两种筛选 chip(f-on 等无切角面)hover 辉光不统一。
- **拍板 D 系列**(逐字单点见计划 §06): 形状与辉光分层 —— clip-path 挪 `::before` 切角绘制层, 本体 `clip-path: none` 让辉光四边闭合; 八组状态语义柔底各写 `::before` 背景(15% alpha 柔底不等价 currentColor/inherit, R6); 全部规则带 `html[data-fx-preset]` 前缀避四皮肤键集守阵(R2)。
- **D4 focus-visible 预留**: 纯 `<span>` chip 无 tabindex, `:focus-visible` 当前不命中 —— 只做样式预留, 键盘化另立件(O5), 禁止本波顺手加 tabindex(R13)。
- **D14 §02 规范漂移另案**: console_hub.css 硬知识未归档 / 26-10-31 计划未回写历史条目 / flux 无截图 diff 门, 三条一律不入本轮。
- **O1 触发 S4(W1-3 预留路径)**: 用户真机目检发现 paused/other/search-hit 状态切角丢失(hover 边线持续可见属行为变化, 经目检裁决接受)—— W1-3 预留的「常态 inset 描边与 sa-no-conf dashed 底边迁 ::before 切角绘制层」被触发落地。f-on 无辉光维持计划 D4 拍板。

## 实现计划

单点在计划档案(Refs)§04 W1-W3 分期与 §08 风险表; W1-3 为预留路径(状态边线迁 ::before), 由 O1 目检触发实施。落点全在 `src/auto_qb/webui/static/flux/css/fx-mount.css`(components.css 700 行红线, R1)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| W1 | site-chip 形状分层(clip-path 挪 ::before + 八组语义柔底 + focus-visible 样式预留 + ::before 补 background 过渡), 提交 399bdb2e | Done(2026-11-10) |
| W2 | 静态守阵 `test_frontend_fx_site_chip_shape_layering`(本体无 clip-path + polygon 在 ::before, 「不设防」口径; 接缝终审后已扩展钉 S4 迁移面)+ e2e `flux-site-chip-shape-glow.spec.mjs`(主判据 computed clipPath, 旁证 boxShadow, crisp 逐层 alpha=0, 三拍稳态 poll), 提交 644f3274 | Done(2026-11-10) |
| 入池 | 分支既有 e2e 失败(ctx-custom 稳定红标准档 + traffic-gap-zones flaky 便签/flaky-ledger 台账), 提交 37c12e00 | Done(2026-11-10) |
| S4 | W1-3 预留路径触发(O1 目检): paused/other/search-hit 的 inset 描边与 sa-no-conf dashed 底边从本体迁入 ::before 切角绘制层, fx-mount.css 452→485 行, 提交 f7f4658c | Done(2026-11-10) |
| 收尾 | 各批评审零 actionable 收口; 用户真机目检全过; 计划翻 Done; 新坑档 clip-path-clips-outer-glow; 基线切片; 本档案 | Done(2026-11-11) |

## 进度日志

### R0 · 立档 (2026-11-11)

四笔提交落地(399bdb2e W1 / 644f3274 W2 / 37c12e00 入池 / f7f4658c S4)。评审 W1 2 轮、W2 4 轮、S4 收口轮均零 actionable。用户真机目检: O1 发现状态 chip 切角丢失触发 S4 边线迁移(hover 边线持续可见经裁决接受)、f-on 无辉光维持 D4、最终全过。全量测试全绿(见 kb.baseline, 基线切片 26-11-11-0314)。遗留: focus-visible 键盘化另立件(O5); §02 三条规范漂移按 D14 另案, 不入本轮。新坑档 `pitfalls/web-ui/clip-path-clips-outer-glow.md`(clip-path 与 box-shadow/filter 外发光互斥, 对策=形状与辉光分层)。

- 2026-11-11 03:13 计划 26-11-10-0921 实施完成收尾: 四笔提交 399bdb2e(W1 形状分层)/644f3274(W2 守阵+e2e)/37c12e00(入池既有 e2e 失败)/f7f4658c(S4 W1-3 预留路径触发, 状态边线迁 ::before 切角绘制层, O1 用户目检发现切角丢失触发); 各批评审零 actionable; 用户真机目检全过(f-on 无辉光维持 D4); 计划翻 Done; 新坑档 clip-path-clips-outer-glow(clip-path 裁 box-shadow 外发光, 对策=形状辉光分层); 全量全绿(见 kb.baseline); 遗留 focus-visible 键盘化(O5)与 §02 三条规范漂移(D14 另案)
- 2026-11-11 03:32 接缝终审 1 minor 修复收口: S4 迁移面零守阵 —— 扩展静态守阵 `test_frontend_fx_site_chip_shape_layering`(+47 行)钉 ::before 三载体/本体三关闭/渐隐过渡段, 红验 2 条留痕, 复评通过; 守阵描述已在子任务状态表 W2 行同步(现含 S4 迁移面)
