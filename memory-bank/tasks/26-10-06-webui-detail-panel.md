# 26-10-06-webui-detail-panel — WEBUI 种子详情面板重构 · 设计模板轮 + 全量实施

**Status:** Done
**Added:** 2026-10-06
**Updated:** 2026-10-07
**Topics:** webui-detail-panel-redesign
**Summary:** 设计模板轮 + 实施轮 + 摸排轮。设计轮产出 15 份可交互单页模板 + `_brief.md` + 汇总报告 26-10-06-0723; 用户拍板 15 套全量实施可切换(试用期取代逐页选型)、挂载点尽量少、选择存 localStorage。实施轮按计划 26-10-06-0838 七阶段完成: S1 核心层(drawer_templates.js 注册表/宿主生命周期/dtHtml 转义/CSS 注入单点/摘要)+ 骨架挂载 + classic 兜底, S2-S6 五页签 × 3 变体 = 15 个自注册文件, S7 收口(全矩阵巡检 283 断言全过 / 删变体演示 / test.full 新基线 / 坑档两篇)。**试用期使用: 面板头部下拉切换器(详情模板/流量模板)按页签选择并记 localStorage(`autoqb.ui.drawerTpl`), 经典版恒在首位可随时回退; 增删一套变体 = 1 个 `shared/drawer_tpl/NN-*.js` 文件 + 三份皮肤 index.html manifest 各 1 行。**〔摸排轮 26-10-07〕对实施产物做静态走查摸排, 汇总报告 26-10-07-0542: 用户点名 4 问题全部确认(4K 横向比例失调 / 变体缺图标 / 收起态不随点击切换种子 / 变体 label 混档位后缀), 新发现 P2×3 + P3×5, 两项复核通过; 修复轮将按报告修复顺序拆小任务派子智能体串行执行。**〔修复轮 26-10-07〕已完成, 按用户拍板独立立档见 [26-10-07-webui-detail-panel-audit-fixes](26-10-07-webui-detail-panel-audit-fixes.md): 8 笔提交修复 Q1-Q4 + P2×3 + P3-4..P3-7(P3-8 属重构批次未做)。**
**Refs:** memory-bank/reports/26-10-06-0723-report-webui-detail-panel-redesign.html,memory-bank/plans/26-10-06-0838-plan-webui-detail-panel-redesign.html,memory-bank/reports/26-10-07-0542-report-webui-detail-panel-variants-audit.html,memory-bank/tasks/26-10-07-webui-detail-panel-audit-fixes.md

## 原始请求

用户命题(详情面板从右侧抽屉改为底部停靠面板之后):

1. **常规页右边空一大块** —— 沿用旧竖向排版(分组卡片 + 单列 label/value 行), 面板改下方后宽度拉满列表宽, 行高堆叠导致右侧大量留白, 信息密度极低。
2. **Tracker/用户/内容三页没设计感** —— 近乎裸 `<table>` 平铺, 无分组、无层级、无状态可视化, 与主列表设计水准脱节。
3. **收起状态疑似没有实际作用** —— 要求代码级论证。

要求逐页出可交互 HTML 设计模板供用户选型拍板。

## 思考过程与决策

- **收起态论证(报告 §收起状态论证)**: 正面证据 —— 收起真实回收头部空间(约 44px), 机制存在; 反面证据 —— 反馈极弱, 且持久化是死数据(只写不回读、重开重置)。结论: **收起有实际作用, 但需三条补强**: ①持久化回读 ②收起态点页签自动展开 ③收起态头部摘要化。三条写进报告「补强建议」供实施轮采纳。
- **模板族形态**: 15 份 = 五页(general / trackers / peers / content / traffic) × 三方向(高 tall=信息全景 / 矮 low=卡片紧凑 / 收起 collapsed=表格化); 统一口径 —— prism ocean 令牌、单文件自包含、dark 主题(模拟真实产品 UI), **每份内置 收起/矮/高 三档高度切换**, 一份即可预览全档。
- **信息增量回收**: 模板不止重排现有字段, 顺带回收「有数据但未展示」的字段(报告 §信息增量)。
- **逐页推荐写进报告, 标注「供拍板」** —— 用户可整页采纳, 也可指定吸收组合(如 general = 02 基线 + 01 英雄行)。
- **质检中修复**: 01-12 号模板缺 `[hidden]` 规则共 12 行 —— `[hidden]` 属性会被显式 `display` 规则压掉, 单文件模板必须自带 `[hidden]{display:none}` 才能保证档位切换生效。
- **实施拍板(2026-10-06, 用户)**: 15 套模板**不逐页三选一, 全部实施可切换**, 用实际试用期代替纸面选型; 两条硬要求 —— **每套模板挂载点尽量少**(增删一套 = 1 文件 + 3 行 manifest)、**选择存 localStorage**(按页签记 id)。报告 §4 逐页推荐降级为拍板点 P-01 备选; 补强二(收起态点页签自动展开)/补强三(收起态头部摘要化)纳入实施, 补强一(开合态回读)因 D1 拍板在案不入范围。
- **实施架构(计划 26-10-06-0838 定稿待拍板)**: 注册表 + 宿主 + 经典版兜底 —— 数据管线(drawer.js fetcher/轮询/FX-29)零改动, 骨架一次性加挂(每页签经典包裹层 + 变体宿主 + 切换器 + 收起摘要条), 核心层 `drawer_templates.js` 管注册表/生命周期/转义/CSS 注入, 15 变体各一个自注册文件。三皮肤 CSS 零改动(变体样式 JS 注入), 锁步面收窄到三份 index.html manifest。

## 实现计划

- **设计轮(已闭环)**: `_brief.md` 调研简报(唯一输入: 现状实现地图 / 令牌 / 产出规格) → 15 份编号模板 01-15 → 汇总报告(论证 + 逐页推荐) → Playwright 真机质检。
- **实施轮(进行中)**: 用户拍板后已出实施计划 [26-10-06-0838](../plans/26-10-06-0838-plan-webui-detail-panel-redesign.html)(注册表 + 宿主 + 经典兜底, S0-S7, 拍板点 P-01…P-06, doc-status Open); 拍板点定案后按计划 S1-S7 实施, 实施会话在本档案追加结论与决策。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 调研简报 `resources/detail-panel-templates/_brief.md`(现状地图 / 令牌 / 规格) | Done |
| 2 | 15 份编号模板 01-15(五页 × 三方向, 三档高度切换) | Done |
| 3 | 汇总报告 26-10-06-0723(收起论证 + 逐页推荐, reports/_index.md 已登记) | Done |
| 4 | 质检: Playwright 真机逐份三档+交互全过; 修 01-12 缺 `[hidden]` 规则 | Done |
| 5 | 用户选型拍板 | Done(26-10-06 拍板: 15 套全量实施可切换 + 挂载点最少 + localStorage 记忆) |
| 6 | 实施轮: 实施计划 26-10-06-0838 | Done(拍板 P-01…P-06 按推荐案全收, doc-status 转 Done) |
| 7 | S1-S7 实施(核心骨架 → 五页签变体 → 收口) | Done(2026-10-06, S1-S7 七笔提交; S7 全矩阵 283 断言全过 + 删变体演示 + 基线 2678+4) |
| 8 | 摸排轮: 新版详情面板问题摸排 + 汇总报告 26-10-07-0542 | Done(2026-10-07, 静态走查零代码改动; 点名 4 问题确认 + P2×3/P3×5 新发现) |

## 进度日志

- **2026-10-07 08:36 修复轮独立立档(用户拍板)**: 报告 26-10-07-0542 的修复轮完成, 按用户裁决独立立档不并入本档案 —— 8 笔提交(`9726b12f..2367555d`)修复 Q1-Q4 + P2×3 + P3-4..P3-7, 收口 test.full 2712 passed + 4 skipped / 99%(基线 26-10-07-0836), 详见 [26-10-07-webui-detail-panel-audit-fixes](26-10-07-webui-detail-panel-audit-fixes.md)。
- **2026-10-06 07:23 设计轮完成**: 15 份模板 + `_brief.md` + 报告 26-10-06-0723 全部就位, 报告登记进 `reports/_index.md`(kb.index 已重建)。零代码改动(未动 `src/` / `config`), 未 commit 等用户指令。
- **2026-10-06 07:5x 收尾 DoD**: 新建 activeContext 切片 `26-10-06-0751-webui-detail-panel-design.md` + 本档案; 报告补 `doc-refs` 反向声明闭环认领链; `kb.docmap --check` 绿(456 份 / 250 专题, 双向闭环; `--topic webui-detail-panel-redesign` 归组报告 Done + 档案 In Progress); test.full **豁免**(零代码改动, 现役基线 `26-10-06-0713` 不变), 改跑 `test.one tests/test_memory_bank.py` 验 KB 守卫 **32 passed**。
- **2026-10-06 08:38 拍板 + 实施计划出稿**: 用户拍板 15 套全量实施可切换、挂载点尽量少、选择存 localStorage(取代报告 §6「逐页选型」路径)。通读报告 + 抽读 drawer.js(1326 行)/drawer.html(286 行)/三皮肤 manifest/app.js 恢复通道/qb_traffic_chart.js 宿主解析后, 出实施计划 [26-10-06-0838](../plans/26-10-06-0838-plan-webui-detail-panel-redesign.html): 注册表 + 宿主 + 经典版兜底架构, 常驻挂载 5 文件约 25 行 + 每变体 1 文件 + 3 行 manifest, S0-S7 分步, 拍板点 P-01…P-06 各带推荐案(含: 初装默认 classic / 06 倒计时全局近似 / 13 注解层省略 / 09 封禁钮省略(已核实后端无 peer 封禁端点) / 14 联动静态 / 摘要条压 44px)。报告 meta 补计划反向声明(仅机械面), 本档案登记拍板与计划。计划 doc-status **Open 待拍板**, 未动任何产品代码, 未 commit。
- **2026-10-06 09:51-16:0x 实施轮 S1-S7 完成(七笔提交, 分支 feature/webui-drawer-templates)**: 各阶段 commit —— S1 核心层与骨架挂载 `e8cb41bc` / S2 general 变体 01-03 `99b7aeb4` / S3 trackers 变体 04-06 `3f5c2fe0` / S4 peers 变体 07-09 + S2 变体监听摘除修复 `1e6e89ee` / S5 content 变体 10-12 `29b9e88f` / S6 traffic 变体 13-15 `b2a85edb` / S7 收口(本提交)。**拍板点执行情况(全部按推荐案落地)**: P-01 初装全 classic(S1: initialDrawerTpl 白名单映射 + 守阵 test_drawer_tpl_classic_default) / P-02 06 倒计时以 detail.reannounce_in 全局值近似并标「全局」 / P-03 13 注解层 v1 省略(限速值文字格, qb_traffic_chart.js 零改动) / P-04 09 封禁钮 v1 省略(迅雷红标保留) / P-05 14 解读栏 v1 静态 / P-06 收起摘要压 44px 头部(核心内置 + 变体可覆写 summary())。
- **2026-10-06 16:3x S7 收口实测**: ①**全矩阵巡检 283 断言全过, 零 pageerror / 零 console.error, 148.3s**(工装在系统临时目录不入仓库; 桩 = scripts/ui_harness.py 管线 + S4/S5 灌数手法 + 直接驱动真实 TrafficSampleModule 采样 60 轮灌流量天文件): prism 全矩阵 = classic + 15 变体 × 五页签 × 三档(收起/矮/高)逐组合断言变体挂载/经典互斥/收起摘要条在场/三档几何(矮<高, 拖 grip 实测); 切换器每页签恰 4 项且 classic 恒首位; **监听不叠加全页面复检**(同页签变体互切后复制单击恰 1 toast + 01 分组折叠单击单翻 + 五页签大循环 3 轮后再复制仍 1 toast); **持久化 e2e**(等价 @playwright/test 冒烟断言, python playwright 落地 —— 本 clone @playwright/test 未装 node_modules, 迁移计划 26-10-06-0708 落地后补挂): 五页签各选变体 → reload → 选择保持且变体重挂; 脏 id(99-dirty/xxx/空串/数字)一律回落 classic, 合法 id 放行; atlas/console 抽查 = 每页签一变体 × 高/收起 + classic 回退, 全过。②**删变体演示(完成判据 2)**: 工作树删 `07-peers-dashboard-tall.js`(manifest 三行未动)→ 守阵红(test_drawer_tpl_registry_wiring + test_frontend_static_bundle_health, FileNotFoundError 抓到缺失)→ 继续 `git rm` 三份 manifest 各去 1 行 → 守阵转绿 → 页面已存 `peers:"07"` 的 localStorage 自动回落 classic(切换器=classic / 变体宿主空 / 经典用户表 58 行接管 / 零报错; 存储里的脏 id 保留不回写, 读侧白名单兜住)→ `git checkout --` 恢复, 守阵转绿。**实测确认「增删一套 = 1 文件 + 3 行 manifest」承诺成立**; 注: 文件+manifest 同删时 wiring 守阵按目录现存文件遍历, 红由「文件删除但 manifest 残留」路径触发 —— 引用缺失守阵(resource scan)与 wiring 守阵分别抓两种半残态。③**test.full 新基线**: **2678 passed + 4 skipped, 覆盖率 TOTAL 99%(16021 语句/166 未覆盖/5472 分支/144 partial), 单次采样 45.37s**(基线切片 `26-10-06-1620-webui-detail-panel-s7`); 中途 4 条 KB 守阵红 = 新坑档未重建索引所致, `kb.index` 重建后全绿(32 passed), `kb.docmap --check` 绿(457 份 / 250 专题)。④**S4 遗留项裁量(结论: 不动 drawer.js)**: peers fetcher 的 `_dtNotify("peers")` 发生在 finally 里 `peersLoading=false` 之前, 空数据时变体 loading 帧要等下一轮 5s 轮询自愈 —— 修它要在四 fetcher 落袋时序上动刀(S1 已封的钩子面), 收益(空数据页签 5s 内的一帧 loading 文案)远小于风险(fetcher 时序是 stale 纪律 + FX-29 咬合面); 按 FX-29 纪律保留现状, 实测巡检未复现可感知异常。
- **2026-10-07 05:4x 摸排轮完成(报告 26-10-07-0542)**: 用户要求对 WEBUI 新版种子详情面板(计划 26-10-06-0838 重构产物)做问题摸排并出汇总报告。方式 = **静态代码走查**(两个子智能体串行: 只读摸排 → 报告撰写), 未真机渲染验证; 开工同步成功, 基线 commit `332c1587`(快进自 `296d5223`)。产出 `reports/26-10-07-0542-report-webui-detail-panel-variants-audit.html`(单文件 HTML dark 主题, reports/_index.md 已登记): **用户点名 4 问题全部确认** —— ①4K 横向比例失调(变体栅格 1fr 等分铺满 + space-between, 无 max-width/宽度断点, 放弃经典 .f-row 固定标签列口径) ②缺图标(drawerGeneralSections() 的 icon 数据被 general 三变体丢弃, traffic 两变体零 svg) ③收起态不随点击切换种子(`drawer.js:848` `if (this.drawer.collapsed) return;` 守卫误伤鼠标路径) ④15 个变体注册 label 混入「(高/矮/收起)」档位后缀并透传 UI 下拉; **新发现 P2×3**(渲染抛错页签空白无降级 / 宽表格 scrollLeft 重渲染归零 / 收起摘要条陈旧数据) + **P3×5**; **两项复核通过**(S2 监听摘除干净、三皮肤接入无缺口)。报告含分阶段修复顺序建议; 修复轮将按该顺序拆小任务派子智能体串行执行(尚未开始)。本轮零代码改动(未动 `src/` / `config`); test.full 实测 2705 passed + 4 skipped / 99% / 56.94s, 基线切片 `26-10-07-0548-webui-detail-panel-variants-audit`(与上基线 26-10-07-0508 全同, 噪声级)。
- **试用期使用说明**: ①切换器在面板头部右侧下拉(种子详情 = 「详情模板」, 流量形态 = 「流量模板」), 五页签各自独立选择, 存 localStorage 键 `autoqb.ui.drawerTpl`(按页签记 id); 「经典」恒在首位, 随时回退。②增删一套变体 = 新增/删除 `src/auto_qb/webui/static/shared/drawer_tpl/NN-<tab>-<slug>.js` 一个自注册文件 + 三份皮肤 `index.html` manifest 各 1 行(装载序: drawer.js 之后、state.js 之前是硬约束); 文件内 `reg.register({id, tab, label, css, render, summary?, notify?, destroy?, slot?})`, id 限 `[A-Za-z0-9_-]`。③删除变体后已存 localStorage 的旧 id 自动回落 classic(白名单兜底, 不报错)。④相关坑档: `pitfalls/web-ui/global-mixin-basetransition-watch.md`(全局 mixin 禁 watch 选项)与 `pitfalls/web-ui/injected-dom-title-migrated-to-aq-tip.md`(变体 DOM 的 title 被断供式迁移)。
