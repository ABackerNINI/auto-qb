# 3398 —— 流量图三挂点控件统一落图下统计栏 + 上限读数移除 + 统计栏贴底 执行基线

> 摘要: 用户动议「全局流量图的视图/纵轴按钮改到下方与种子流量图对齐; 调小流量图统计栏(上传/下载图例那栏)与下方元素的间隔; 移除纵轴上限字样(全局同样跟进)」。落地(纯前端静态层 + 测试侧, Python 产品代码零改动): ①`tpl/drawer.html` 流量形态头部摘掉 `<aq-qb-ctl>`(头部回归纯标题), 统计栏 `.hist-summary` 与 `.qb-statctl` 去 scope 门(三挂点恒渲染); ②上限读数整链退役(`qb_traffic_chart.js` 删 `qbYAxisCapText` computed / `tpl/drawer-head.html` 删 `.qb-tools-hint` / 三皮肤 CSS 删规则); ③三皮肤删头部挂点死规则(`.drawer-head:has(> .qb-tabs)` 族) + `.drawer-body.is-traffic` 底部内边距 20→8px; ④守阵改写口径(头部调用点反挂控件 + 挂点数 2→1 + 上限读数反回潮), 零新增测试函数。e2e fast 166 用例全绿; prism 全局/种子两形态截图比对通过(控件同排同位 / 上限字样消失 / 统计栏贴底)。
> 基线时间: 2026-10-16 01:31

**Refs:** memory-bank/activeContext/26-10-09-0740-webui-qb-traffic-seed-header-controls.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` -> 已同步 2a3b3e13; 工作树含本轮改动时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3398 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**

| 面 | 语句 | 未覆盖 | 分支 | partial | 覆盖率 |
|---|---|---|---|---|---|
| TOTAL | 17337 | 182 | 5846 | 158 | 99% |

- 耗时: 153.31s(单次采样, 区间口径见 `testing/baseline.md`)
- e2e: `npm run test:e2e:fast` 166 passed(改动面为前端静态层, 按门禁口径补跑)
- 本轮零新增测试函数; 守阵只改写既有断言口径(`tests/test_webui_static_dom_panel.py` 内流量图控件落点/上限读数相关断言)。
- Linux (WSL 沙箱) 本轮未重测 —— 改动全在纯静态前端层与静态守阵, 无平台分支。

## 包内脚本测试

- 本轮未触碰 `.commands/` 与 `.agents/skills/commands/`, 未跑 `test.pkg`; 提交闸门按 match 规则自判。
