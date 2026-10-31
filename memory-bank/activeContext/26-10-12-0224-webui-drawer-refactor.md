# 种子详情面板重构(字符串 DOM 变体 → Vue 面板) · W5 已落地

> 摘要: 用户命题「按推荐实施 [计划 26-10-11-2106]」= 拍板点 **D1–D4 一律取推荐项 A**。**W0** 冻结契约与验收基线; **W1** 数据层抽离(A/B DOM dump 逐字节等价); **W2** 四页签 Vue 重建 + 三列表接壳(拍板「全部一起做」+「Vue 连变体一起声明式实现」); **W3** 流量页签与形态收敛(拍板「缺陷留到 W5」); **W4** 合并双列与右键模板选择(单一状态源 + 删双份判据)。**W5**(本轮 26-10-12-0224)= **变体退役与声明式密度档**: 15 个过程式变体(`drawer_tpl/` 15 文件 5739 行)与插件挂载机械(`_dtMount*`/`_dtSync`/`_dtNotify`/`dtHtml` 等)整体删除, 「换版式」收敛为每页签 2 档的密度档(`DRAWER_DENSITY` 一张表: classic / compact, 描述符 `{id,label,cls,raw,hint}`); 旧 id 显式迁移(tall→classic / low·collapsed→compact / 脏值→classic, 读侧一次归一); 结构开关(raw/hint)走 `v-if` 真隐藏; 换档 = Vue 响应式(无通知/重挂)。`test.full` 3122 passed(worktree 收集清单 diff 逐条对账闭合)+ e2e 156 passed(166 − 退役 14 + 新增 4)+ 红验两条均注入即红/还原即绿。**W5 验收达成: 每页签档位切换生效并持久化; 旧 id 不报错、有明确迁移去向; 停手点守住(不新增过程式字符串构建)**。数字见基线切片。仅剩 W6(收口与退役)。
>
> 最后活动: 2026-10-12 02:24

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/testing/baselines/attachments/26-10-12-0224-webui-drawer-refactor-w5.md

## 本轮完成 (W5)

- **声明式密度档**: `drawer_templates.js`(624→约 250 行)收敛为「选择层」—— `DRAWER_DENSITY` 表(每页签 `tiers: [classic, compact]` + `legacy` 迁移映射)+ `window.AQB_DRAWER_DENSITY` 三 API(options/tierOf/normalize)+ `dtInjectCss("00-density")` 密度 CSS。组件只消费描述符: 密度类 `dd-compact` 挂组件根(`drawerTier(tab).cls`), 结构开关 `raw`/`hint` 走模板 `v-if` 真隐藏(general `details.drawer-raw` / content `.drawer-toolbar-hint`) —— 不是 CSS 藏(计划 §08 R7)。
- **插件机械退役**: `drawer_tpl/` 目录(15 文件)+ 三份 manifest 变体段删除; `_dtMount*`/`_dtSync`/`_dtNotify`/`_dtRender`/`dtHtml`/`dtRaw`/KIT/HELPERS 全删; `drawer.js` 删 `_dtSync` 与 `_dtUnmountAll`; `drawer_store.js` 删 4 处通知; `state.js` watcher 种子支路 `if (!s) return;`; `menu.js` 删 `data-dt-host` 分支(`_drawerMenuColByX` 保留)。
- **守阵同轮改版(不放宽)**: 收集 45→27 —— 删 10 条变体守阵; `test_drawer_tpl_registry_wiring` 改密度档接线钉; 新增 `test_drawer_tpl_facility_retired`(退役确认, **活代码形态锚定**防复活)与 `_DT_DENSITY_NODE_PROBE`(node 电池: normalize 迁移 / readSel 脏值 / dtMenuPick 白名单 / drawerTier 结构开关); 七份守阵文件变体读取面同轮改, 收口轮 154 passed + 2 skipped。
- **e2e**: 新增 `drawer-density.spec.mjs`(旧 id 混预置迁移 + 右键切档/落盘/刷新持久化/回切, ×2 皮肤); `drawer-merge` 用例⑤与 `drawer-tables` 用例③改密度档口径(后者改**效果判别** —— 各页签选项集同名后菜单归属只能靠「落谁的 localStorage 记忆」判); 4 条变体专用 spec 退役(7 用例 × 2 皮肤 = 14 执行)。
- **验收**: `test.full` = 3122 passed + 4 skipped / `TOTAL 16517 151 5626 134 99%`(对账: HEAD 3130 + W3 未提交守阵 1 + 本轮 1 − 退役 10 = 3122 ✓); e2e = 156 passed + 0 failed + 10 skipped(166 − 14 + 4 ✓); 红验两条(RC1 迁移去向错 / RC2 raw 开关失效)均注入即红、还原即绿。

## 三处非显然的判断(下轮别再踩)

1. **红验注入与长跑验证不得并行** —— 首轮 dev.e2e 的 2 条失败是注入窗口撞车(dev.e2e 运行期间恰覆盖 RC2 注入), 表现与真缺陷一致但源码已还原因果链颠倒; 还原后重跑全绿。此前波次串行没踩过, 本轮并行省时撞出假红。
2. **各页签密度档选项集同名(经典/紧凑) ⇒ 右键菜单归属只能靠效果判别** —— 旧变体时代「左列不出右列的变体」的排除断言全部失效, e2e 改锚「选紧凑后落谁的 localStorage 记忆」; 若菜单页签解析接错(固定 general)菜单照样弹出且不报错, 只有这条效果断言能抓到。
3. **traffic 页签在 e2e 不可达**(`v-if="qbTrafficOn"` 桩不启用) —— 密度档的 traffic 腿由静态 node 电池(normalize/tierOf)承接, e2e 预置里写 `traffic: "14"` 会在找页签按钮时超时假红; 同理 dt06 逐行倒计时等**变体独有能力**随退役消失且无 e2e 等价物, 移交待办。

## 待办 / 移交

- **W6(最后一波)待起 = 收口与退役**: ① 删 `drawer_templates.js` 整文件 —— 菜单选项源/读侧归一(`initialDrawerTpl`)/显隐判据(`dtHostOn` 等)迁 `drawer.js`, **00-core 合并 CSS + 00-density 密度 CSS 迁三皮肤**(`.drawer-split` 族 + `dd-compact` 族 + 2400 封顶; 变体专属 `.dt-tpl` 限宽已随退役消失); ② 摘 `qb_traffic_chart.js` 谓词冻结豁免换吃 `drawerIsTraffic`(`test_frontend_drawer_form_judge_single_point` 豁免注释同步摘); ③ 坑档收口(`drawer-switch-flicker` / `vif-host-node-stale` / `variant-singleton-shadow` 标「随重建退役」, 本轮已给 `sticky-scrollpad-inset` / `esc-attr-quote-dead-class` 加退役注); ④ 验收 = 终态判据「抽屉只剩一套渲染技术」。
- **dt06 逐行汇报倒计时**: 变体独有能力(逐行「下次汇报」列)随退役消失, 经典列表无等价物(静态守阵同步删除) —— 若用户需要该口径须在经典 trackers 列表加列(新需求, 不属重构范围), 待用户表态。
- **债务(承接, 不拦提交)**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W5 各加一条); `kb.check` 切片数 > 70。两项均需另开新会话收口。
- **工作树**: W2 + W3 + W4 + W5 四轮改动均未提交(用户未要求 commit)。
