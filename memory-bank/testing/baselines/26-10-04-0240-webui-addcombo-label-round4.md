# 基线切片 26-10-04-0240 — 添加种子三下拉 label 闪烁第四轮修复(JS 收层守卫单点)

> 摘要: 用户报 594e247f(三修)后真机仍闪。探针自校验证明三修代码在 Chromium 人手时序下干净,
> 用户症状 = 浏览器跑的是旧模板(SPA 长开页签资源以页面加载时刻为准)。加固 = 收层 JS 单点守卫
> `_popBlurShouldHold`(焦点已回本族输入框 / 本族 label 转发 click 仍在途 → 不收), 模板修饰符
> 缺位时独立根除闪烁, 任何模板/JS 代际混合都安全。

- 时间: 2026-10-04 02:40 (GMT+8); 会话起点 sync 至 908fbf28, 提交前 stash→sync 合并远端 2b10581a
  后于新基线重测(数字与合并前一致, 见下)
- 分支: develop @ 2b10581a(+ 本轮未提交改动: add_torrent.js / dialogs.js / test_web.py)
- 命令: `commands run test.full`
- 实测: **2419 passed + 3 skipped, 31.86s, 覆盖率 99%**(合并 2b10581a 后重测; 与 908fbf28 基线
  首测 29.34s 同数, 远端三笔为报告/计划/流量图修复, 不动本面)
- 真浏览器走查(Playwright + scripts/ui_harness.py 桩后端, click delay=150ms 人手时序, rAF 菜单翻转时间线):
  - **探针自校验**: 摘掉 `@mousedown.prevent` → 完整闪烁链复现(focusout@+0.2ms → 收层@+65ms →
    回焦重开) —— 探针灵敏度实证, 阴性结果可信
  - **守卫 vs 旧模板(修饰符摘掉态)4/4**: 按住 150ms 点 label 零翻转 / 点空白照常收 / Tab 照常收 /
    记录 600ms 过期后 blur 照常收
  - **真实状态全量回归 24/24**: 三皮肤(atlas/prism/console) × 8 项(三字段「开着点/关着点/未聚焦点」
    + 点空白收层 + 互斥双向 + meta 分类同款)
- 改动面:
  - `src/auto_qb/webui/static/shared/add_torrent.js` — mounted 挂 mousedown capture 记录器(unmounted
    对称移除) + `_popBlurShouldHold(ids)` 单点 + addPopBlurClose 定时器体接守卫(三字段 id 名单)
  - `src/auto_qb/webui/static/shared/dialogs.js` — metaCatBlurClose 同款接守卫(["meta-category"])
  - `tests/test_web.py` — combo 守阵新增第 7 组(JS 守卫接线断言); 拖拽守阵 mounted 断言改子集语义
  - `memory-bank/pitfalls/web-ui/combobox-focusout-close.md` — 第四轮条目(复发:2, 交付代际教训)
- 未验证面: 真机(真实 qB + 真实数据 + 用户实际浏览器)走查待用户执行 —— **必须先整页强刷(Ctrl+F5)**
