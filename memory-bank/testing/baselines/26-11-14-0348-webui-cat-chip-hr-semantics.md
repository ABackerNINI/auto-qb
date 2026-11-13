# 6102 —— S1-S4 实施收口基线

> 摘要: webui 分类 chip HR 语义批(计划 26-11-14-0001 S1-S4): test.full 6102+2 覆盖 99%
> 基线时间: 2026-11-14 03:48

## 验收数字

`commands run test.full` 实测(2026-11-14 03:45, clone2 本机, 计划 26-11-14-0001 S1-S4 五笔提交 f9c5c752..cd14ffe6 收尾):

- 汇总行: `6102 passed, 2 skipped in 147.42s (0:02:27)`
- TOTAL 表: `27115 stmts / 65 miss / 9480 branch / 69 miss / 99%`
- 对照上切片(26-11-14 00:05, 6084+19, 另一宿主): 本轮 pytest 面净增 1 条守阵
  (test_frontend_cat_chip_hr_semantics_css, T4), 总收集数 6102+2=6104 对 6084+19=6103;
  passed/skipped 分布含两宿主环境条件 skip 组差异, 非本批引入
- e2e 面(同批实测, 非 test.full 口径): `commands run dev.e2e -- e2e/flux-cat-chip-hr-semantics.spec.mjs`
  1 passed(5.0s), 红绿双验 4 组逐条独立(删规则/删绑定即红、恢复即绿; Windows dev.e2e 轨,
  本机无 docker, test.linux-env 失败行实证)

## 本改动面

- `src/auto_qb/webui/views.py` — hr_view_fields 两分支各 +2 现算键 hr_category/hr_category_done
  (S1, f9c5c752)。
- `tests/test_web_hr_views.py` — 两分支键集恒等 + 排除种子空串 + 三种子分类键断言(S4-3,
  随 S1 同笔)。
- `src/auto_qb/webui/static/shared/decorate.js` — +catClass/hrExclClass(S2, ac554ba2)。
- `src/auto_qb/webui/static/shared/hr.js` — +hrExclTip(判定门单点复用 hrExclClass, 终审修复
  cd14ffe6)。
- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html` / `xtpl.html` — 组行/torrent/member
  行 cat+tag 5 处 :class/:title 绑定(S2)。
- `src/auto_qb/webui/static/shared/drawer_tpl/01-general-hero-tall.js` — 抽屉 hero HR 分类
  chip 2 行(S2)。
- `e2e/drawer-general-variants.spec.mjs` — 桩补 hr_category/hr_category_done 空键(S2)。
- 四皮肤 CSS(flux/atlas/console components.css + prism views.css) — cat-chip.hr-* 镜像 +
  hr-excl 合并规则 + 行状态 :not() 让路(S3, 276458be; flux/atlas 恰 700 行、prism 恰 818 行
  达体量守阵冻结值)。
- `tests/test_webui_static_skins_widget.py` — +test_frontend_cat_chip_hr_semantics_css
  (S4, 2ff9cf99)。
- `scripts/ui_harness.py` — +_inject_hr_category 桩注入(S4)。
- `e2e/flux-cat-chip-hr-semantics.spec.mjs` — 新 spec, computed 判据四断言(S4)。
