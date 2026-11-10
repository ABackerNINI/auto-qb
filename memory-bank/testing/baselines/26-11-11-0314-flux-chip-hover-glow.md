# 5913 passed + 2 skipped (149.47s, 覆盖率 99%) —— flux chip hover 辉光统一实施完成全量基线

> 摘要: flux chip hover 辉光统一实施完成全量基线
> 基线时间: 2026-11-11 03:14
**Refs:** memory-bank/tasks/26-11-11-webui-flux-chip-hover-glow.md

## 验收数字

`commands run test.full` 实测输出誊写:

```
TOTAL                                                26254     48   9150     58    99%
5913 passed, 2 skipped in 149.47s (0:02:29)
```

## 本改动面

- `src/auto_qb/webui/static/flux/css/fx-mount.css`: site-chip 形状分层 —— 本体 `clip-path` 挪 `::before` 切角绘制层(本体 `clip-path: none` 让 hover 辉光四边闭合), 八组状态语义柔底落 `::before` 背景, focus-visible 样式预留, ::before 补 background 过渡(提交 399bdb2e); paused/other/search-hit 的 inset 描边与 sa-no-conf dashed 底边从本体迁入 `::before` 切角绘制层(提交 f7f4658c, 由用户真机目检触发; hover 边线持续可见属行为变化, 经目检裁决接受)。全文件 391→485 行, components.css 700 行红线未触碰。
- `tests/test_webui_static_skins_skin.py`: 新增 `test_frontend_fx_site_chip_shape_layering`(本体无 clip-path + polygon 在 ::before, 「不设防」口径)(提交 644f3274)。
- `e2e/flux-site-chip-shape-glow.spec.mjs`(新): 主判据 computed `clipPath`, 旁证 `boxShadow`, crisp 逐层 alpha=0, 三拍稳态 poll(提交 644f3274)。
- `memory-bank/issues/`: 分支既有 e2e 失败入池(ctx-custom 稳定红标准档 + traffic-gap-zones flaky 便签/flaky-ledger 台账)(提交 37c12e00)。
- 知识库记账: 计划 `memory-bank/plans/26-11-10-0921-plan-flux-chip-hover-glow.html` 翻 Done + §10 实施完成条目; 任务档案 `memory-bank/tasks/26-11-11-webui-flux-chip-hover-glow.md`(新); 坑档 `memory-bank/pitfalls/web-ui/clip-path-clips-outer-glow.md`(新) + `kb.index` 生成物; 收尾切片; 本切片。
- 各批评审(W1 2 轮 / W2 4 轮 / S4 收口轮)均零 actionable; 用户真机目检全过(f-on 无辉光维持计划 D4 拍板)。
