# 26-11-14-webui-flux-chip-glow-ancestor-clip — flux 分类/标签 chip hover 辉光绘制层统一实施(祖先裁剪放行 + H&R 竖线迁层)

**Status:** Done
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** flux 分类/标签 chip hover 辉光绘制层统一实施: 祖先 overflow:hidden 放行(clip + overflow-clip-margin)与 H&R 竖线迁 ::before, 像素采样 e2e 红绿双验 + 静态守阵; 计划 26-11-12-1012 S1–S6 全期落地
**Topics:** webui-flux-chip-glow-ancestor-clip
**Refs:** memory-bank/plans/26-11-12-1012-plan-flux-chip-glow-ancestor-clip.html, memory-bank/pitfalls/web-ui/ancestor-overflow-clips-descendant-glow.md, memory-bank/pitfalls/testing/commands-e2e-arg-passthrough-three-dashes.md, memory-bank/testing/baselines/26-11-14-0428-flux-chip-glow-ancestor-clip.md, memory-bank/active-context/26-11-14-0430-flux-chip-glow-ancestor-clip.md

## 本篇只回答

计划 26-11-12-1012 的实施怎么落地(S1–S6 各步结果与评审留痕)、S5 目检结论、还剩什么没做。方案与取舍单点在计划档案(Refs, §01–§07 D1–D8), 本篇不复述; 与旧专题档案 26-11-11-webui-flux-chip-hover-glow(site-chip 形状分层)是同一目标的前后两期, 旧件按计划 I6 不回写。

## 原始请求

1. 用户立项实施计划 26-11-12-1012(flux 分类/标签 chip hover 辉光绘制层统一: 祖先裁剪放行 + H&R 状态竖线迁层 + 像素级红绿双验), 按 S1–S6 分期实施。
2. S5 真机目检由用户执行裁决; 全部完成后按收尾 DoD 归档(本档案)。

## 思考过程与决策

- 范围与修法拍板(D1–D8, 逐字单点在计划 §06): 仅改 flux; 新规则全落 `fx-mount.css` 且一律带 `html[data-fx-preset]` 前缀(components.css 恰 700 行禁净增, R1); 零新增令牌(I2); S1 = `overflow:clip + overflow-clip-margin:16px` 覆盖 `.g-tags/.m-tags/.g-cat/.m-cat`(不用 visible/:has(), D5); S2 = H&R 竖线迁空闲 `.tag-chip::before`(仿旧计划 S4, D6); S3 = 独立像素采样 e2e + 红绿双验(不引入 toHaveScreenshot, D3); I6 = 旧计划 26-11-10-0921 正文/状态/拍板记录一律不动。
- 实施期批出计划 §04 自身缺口一处: RM 媒体块渐隐过渡段未写入 S1 步骤 —— 按 §01 算成②「与 site-chip S4 迁层同构」承诺在 fa0eea6d 补齐(令牌逐字沿用同文件 site-chip::before 先例), 即第一批评审留痕里的「修 1」。
- S3 判据全用同一页面内 A/B 相对亮度差(放行态 vs 页内注入 hidden 基线), 不写绝对 RGB 常量(I7); fixture 走 `scripts/ui_harness.py` 内存注入(add_tag/add_tag_for_satisfied = hr-e2e, 标签池加位 3), 不改磁盘树; 实施中发现 exclude_auto 冲突(首案撞 auto_managed_tag_rules 精确集会清空 add-options 候选)改位 3 池名后 add-options-recent-order 期望序逐字不变。

## 实现计划

单点在计划档案(Refs)§03 分期表 + §04 S1–S6 步骤; 收尾 DoD = 计划 §04 S6(本档案即其产物)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1+S2+S4 | `fx-mount.css` 祖先裁剪放行 + H&R 竖线迁层 + RM 渐隐段(+29 行, 485→514) + 静态守阵 `test_frontend_fx_tag_cat_chip_glow_layering`(+96 行), 提交 fa0eea6d; 评审 blocker 0 / 修 1 / 检 1/1 / 轮 2 | Done(提交 fa0eea6d) |
| S3 | `e2e/flux-tag-cat-chip-glow.spec.mjs`(531 行, 3 test: S1 computed 四容器 / hover 辉光四带像素 / S2 竖线两态 + 本体共用 stack) + `scripts/ui_harness.py` fixture 注入(+22 行), 提交 bf95eefb; 评审 blocker 0 / 修 2 / 检 3/3 / 轮 2 | Done(提交 bf95eefb) |
| S5 | 真机目检(dev.harness 桩数据): 三档 preset × 三种 chip × H&R 两态, §05 观察项 O1 由 S3 computed+像素双验闭合, O2–O4 目检闭合, O5 一次跑绿零调参(本轮容器软渲染单环境), O6 维持范围外; 用户裁决 pass | Done(2026-11-13, 用户目检) |
| S6 | 收尾: kb.wrap / 本档案 / 坑档两份 / 计划收档 Done / test.full + 基线切片 / kb.index | Done(2026-11-14) |

## 进度日志

### R0 · 立档 (2026-11-14)

两笔提交落地(fa0eea6d S1+S2+S4 / bf95eefb S3); 红绿双验两轮红验各自 FAILED 后逐字复原(git diff src/ = 0); S5 用户目检 pass(2026-11-13); 收尾立坑档两份(`ancestor-overflow-clips-descendant-glow` 祖先 overflow:hidden 裁后代外发光 / `commands-e2e-arg-passthrough-three-dashes` 透传三连 --), 计划 26-11-12-1012 翻 Done(§10 R4), 全量测试全绿(见 kb.baseline 最新切片, 本批新建)。

遗留: ① 分类 chip 具备对等 HR 效果 = 另案 issue(feat/standard, Open 未认领, 计划 §02 aside 口径, 不建认领链); ② D4 范围外三件另案(focus-visible 键盘化 / 旧计划 §02 三条规范漂移 / 四皮肤统一); ③ `commands run test.linux-e2e` 透传单 spec 需三连 `-- -- --`、`--grep` 含 `|` 被 /bin/sh 解析 —— 已立坑档, 引擎面是否收录专用 task id 待主会话裁决(涉及 `.commands/` 代码面, 不在收尾范围)。

- 2026-11-14 04:30 S6 收尾落地: 两笔提交(fa0eea6d S1+S2+S4 / bf95eefb S3)评审收口, S5 用户目检 pass, 计划 26-11-12-1012 收档 Done(§10 R4), 新坑档两份(祖先 overflow 裁辉光 / e2e 透传三连--), 全量基线切片 26-11-14-0428 落位, 任务档案立档并翻 Done
