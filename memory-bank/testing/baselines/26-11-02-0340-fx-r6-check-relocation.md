# 4806 —— R6 快勾归位后全量

> 摘要: R6 快勾归位后全量
> 基线时间: 2026-11-02 03:40
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-02 03:40, R6 精修轮后):

```text
TOTAL                                                22511    184   7722    141    99%
4806 passed, 10 skipped in 129.26s (0:02:09)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 本轮改动面(前端静态 CSS/HTML)无新测试; 守阵 test_webui_static_skins.py 全绿,
  另跑临时 Playwright 真机验证 18/18(桩服务 8137, flux 选中行无勾标/checkbox 快勾
  computed/hb-switch 排除/indeterminate/RM 降级/showcase D4-6 归位+原语契约; 脚本不入库)。

## 本改动面

- `src/auto_qb/webui/static/flux/css/fx-mount.css`: R2 精修 V3 的行首格 `::after` 勾标
  (.group-row/.member-row.selected > :first-child)与私有 fx-check-pop keyframes 退役;
  同段重写为 D4-6 checkbox 快勾真落地 —— `html[data-fx-preset] input[type="checkbox"]:
  not(.hb-switch input)` 全量自绘(appearance:none 方格 + checked/indeterminate accent 底 +
  内联 SVG 贴图勾形/短横 + disabled/focus-visible 态), 动效(pop 复用 fx.css fx-check-pop +
  background-size 划线近似)收进 RM no-preference 媒体块。
- `src/auto_qb/webui/static/fx/showcase.html`: D4-6 注册项自 d4 挪入 d5(sec/ctor/demo 改
  ctl), makeRows 摘除 check 分支与 .done 死样式(frtChkPop keyframes + RM 块引用), 新增
  makeCtl 构造器(未选/已选两格, 走 fx.css [data-fx~="check"] 原语契约), buildSample 分发
  加 ctl, d4/d5 sec-note 与 mech 构造器清单同步, D4-6 meta.states 记误归类归位注。
- 无 .py 改动; memory-bank 计划档案精修轮 R6 实录另落。
