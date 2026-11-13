# 6085 passed + 19 skipped —— flux 分类/标签 chip 辉光祖先裁剪放行实施完成全量基线

> 摘要: flux 分类/标签 chip 辉光祖先裁剪放行实施完成全量基线(计划 26-11-12-1012 S1–S6 收尾批)
> 基线时间: 2026-11-14 04:28
**Refs:** memory-bank/tasks/26-11-14-webui-flux-chip-glow-ancestor-clip.md

## 验收数字

`commands run test.full` 实测输出誊写(2026-11-14, node PATH 前缀):

```
TOTAL                                                27113     219   9480     89    99%
6085 passed, 19 skipped in 118.79s (0:01:58)
```

## 本改动面

- `src/auto_qb/webui/static/flux/css/fx-mount.css`(+29 行, 485→514, components.css 700 行红线未触碰): S1 四容器 `.g-tags/.m-tags/.g-cat/.m-cat` `overflow:clip + overflow-clip-margin:16px` 祖先裁剪放行; S2 H&R 竖线迁 `.tag-chip.hr-pending/.hr-done::before`(补 position:relative, 本体 box-shadow:none); RM 媒体块渐隐过渡段(评审批出计划 §04 缺口, 按 §01 算成②补齐)(提交 fa0eea6d)。
- `tests/test_webui_static_skins_skin.py`(+96 行): 新增静态守阵 `test_frontend_fx_tag_cat_chip_glow_layering`(9+2 断言点逐字钉 S1/S2/RM 规则体), 同步该文件头部测试计划清单(提交 fa0eea6d)。
- `e2e/flux-tag-cat-chip-glow.spec.mjs`(新, +531 行): 3 test 钉 S1 computed 四容器 / hover 辉光四带像素(同一页面内 A/B 相对亮度差) / S2 竖线两态 + 本体共用 stack; 红绿双验两轮(overflow 回退 hidden 双红 / 删 S2 迁层三段竖线红, 逐字复原后全绿)(提交 bf95eefb)。
- `scripts/ui_harness.py`(+22/-1 行): fixture 内存注入 `add_tag = add_tag_for_satisfied = "hr-e2e"`(标签池加位 3, 避开 exclude_auto 精确集冲突), 不改磁盘树; 抽屉徽章断言面经 stubDetail route 补丁双重绝缘(提交 bf95eefb)。

口径注记: e2e(playwright)数字不进基线口径, 计划 26-11-12-1012 明示锚 Windows 侧; 本切片只记 pytest 全量实测。
