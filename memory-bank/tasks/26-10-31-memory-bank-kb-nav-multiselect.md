# 26-10-31-memory-bank-kb-nav-multiselect — kb.nav 多选与批量右键菜单

**Status:** In Progress
**Added:** 2026-10-31
**Updated:** 2026-10-31
**Summary:** kb.nav 台账加多选(Ctrl/Shift 手势, 主表+置顶区双区同亮, 普通单击不清多选)与批量右键菜单(行∈选区→整集合, 文案带 N, 复制每行一个/打开 >5 confirm/pin·hide 幂等), 辅助件已选 N chip + Esc 末档 + Ctrl+A; 守阵 +6, 计划 26-10-31-0143
**Topics:** memory-bank-kb-nav-multiselect

## 原始请求

1. 「kb.nav添加多选功能, 且需要支持多选右键菜单, 比如多选后右键"复制仓库路径"可以复制多个路径, 每行一个. 其它的右键菜单同理. 先 grilling 一个修改计划」
2. Q2 追加: 多选范围**包括置顶区**; Q3/Q5 交互参照 auto-qb webui 设计(不必全套照搬); Esc 清多选, 左键单击清多选容易误触(拒绝)
3. Q7 追加: 批量「打开原文」超过 5 个时二次弹窗确认; 其余按推荐

## 思考过程与决策

- grilling 两轮 13 问全部拍板(D1-D14, 全表见计划档 §06), 关键改判: D2 置顶区纳入 / D3 普通单击不清多选 / D7 打开 >5 confirm / D14 确认形式用原生 `window.confirm`(零新增 UI)
- 交互口径单点参照 auto-qb webui 既有实现: `selection.js` onTorrentClick(普通点击不选中/不清选, Ctrl 切换, Shift 并入且锚点不动)与 `menu.js` CTX-03(行∈选区→批量菜单, 右键不改选区, 打开时快照)
- 计划档: memory-bank/plans/26-10-31-0143-plan-kb-nav-multiselect.html(已翻 Done)

## 实现计划

单期落地(计划 §04 六步), 全在 nav_page.html + tests/test_kb_nav.py, 服务端零改动: ①S.multi/multiAnchor 会话态 + msel 渲染(双区) → ②Ctrl/Shift 点击手势(先于改 S.sel, 普通单击落锚点) → ③ctxTargets 目标解析单点 + openCtx 冻结快照 + 文案带 N → ④批量动作分发(pin/hide 幂等, copyPaths 可见序, openLinks confirm) → ⑤辅助件(chip/Esc 末档/Ctrl+A/setView 清空) → ⑥守阵扩条 + test.full + 基线切片

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 状态与渲染: S.multi/multiAnchor + msel 双区挂类 + tr.msel/sel.msel CSS | Done(2026-10-31) |
| 2 | 点击手势: 主表+置顶区 Ctrl/Shift 分支, 普通单击不动 S.multi | Done(2026-10-31) |
| 3 | 右键批量升级: ctxTargets + dataset.links 快照 + 批量文案 N | Done(2026-10-31) |
| 4 | 批量动作: togglePinBatch/toggleHideBatch(幂等)/copyPaths/openLinks | Done(2026-10-31) |
| 5 | 辅助件: #mselChip / Esc 退栈末档 / Ctrl+A selectAllVisible / setView 清空 | Done(2026-10-31) |
| 6 | 守阵 +6 + test.full 全绿 + 基线切片 26-10-31-0219 + Playwright 冒烟全过 | Done(2026-10-31) |

## 进度日志

### R0 · 立档 (2026-10-31)

- grilling 13 问拍板 → 计划档 26-10-31-0143; 同会话全段实施落地: 壳 nav_page.html(状态/手势/菜单/批量/辅助件) + tests/test_kb_nav.py +6 守阵; test.full 全绿, 实测数字见 kb.baseline(切片 26-10-31-0219); Playwright 无头真机冒烟 22 项全过(tmp-analysis/nav/smoke_multiselect.js); 计划翻 Done

### R1 · 验收返工 (2026-10-31)

- 用户起桩验收报两处: ①鼠标单击强调左条与多选左条同色相只差明度, 容易搞混 → msel 改专用靛蓝族(--msel-*,
  真值取 auto-qb galaxy --sel-*, 照 views.css R10-07「两态同色相只差明度必混淆 → 色相分家」口径), 满亮左条
  (多选=批量目标取最醒目态), chip 同步; ②批量打开被浏览器拦截静默失效 → openLinks 记账拦截(open 返 null)
  走 showError 引导允许弹窗(Esc 收)。坑档新条目 pitfalls/web-ui/layout-css.md「平行两态同色相只差明度」;
  守阵断言扩两处; 冒烟 24 项全过; 基线切片 26-10-31-0318。

### R2 · 验收返工 (2026-10-31)

- 用户报: Shift 连选触发浏览器原生文字选中, 页面大部分文字被选 → #aRows/#pinZone 挂 mousedown 守卫
  (浏览器在 mousedown 期扩展选区, click 挡已晚) + 两处 click shift 分支 preventDefault 双保险;
  普通点击不挡(标题照常可选中复制)。守阵扩三处断言; 冒烟 +1(getSelection 为空) 25 项全过;
  基线切片 26-10-31-0333。
