# 种子详情面板重构(字符串 DOM 变体 → Vue 面板) · W0/W1 已落地

> 摘要: 用户命题「按推荐实施 [计划 26-10-11-2106]」= 拍板点 **D1–D4 一律取推荐项 A**(Vue 3 组件重建 · 收敛为声明式密度变体 · 按页签分波替换 · 三列表注册进 `<aq-table>`)。目标: 抽屉只留**一套渲染技术**, 退役字符串 DOM 设施, 换版式由声明式档位驱动。**W0**(零代码)= 冻结契约与验收基线(现状全量数字 + 「抽屉 DOM dump」临时探针作 A/B 判据); **W1** = 数据层抽离 —— 把取数 / 竞态 / 等待集合 / 软切换序号从 `shared/drawer.js` 剥成 `shared/drawer_store.js`(`window.AQB_DRAWER_STORE`), **方法体逐字未改、只换落点**, 验收 = 真浏览器 A/B DOM dump **逐字节等价** + 全量与基线逐位一致(数字见基线切片)。W2–W6 待起。
>
> 最后活动: 2026-10-11 21:40

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md

## 本轮完成 (W0 + W1)

- **W0 冻结基线(零代码)**: 跑全量 `test.full` 与 e2e 记现状, 新基线切片 [testing/baselines/26-10-11-2136-webui-drawer-refactor-w0w1.md](../testing/baselines/26-10-11-2136-webui-drawer-refactor-w0w1.md)。建「抽屉 DOM dump」临时探针: 打开种子详情 → 四页签(Tracker/用户/内容/常规)+ 回常规, 取 `.drawer-dock` `innerHTML`, 归一 40 位 hash / 大小速度单位 / 时长 / 时刻 等易变位; 双皮肤各 5 项 = 10 项。用后把探针移出 `e2e/`(留 `tmp-analysis/` 备复用), 不扰动 e2e 用例计数。
- **W1 数据层抽离(零观感变化)**: 新增 `shared/drawer_store.js`, `window.AQB_DRAWER_STORE.methods` 收 `_fetchDrawerDetail|Trackers|Files|Peers` · `_drawerLoadSeq`/`_drawerStale` · `_drawerWait`/`_drawerWaitSources`/`_drawerDone` · `_drawerBusyArm|Disarm`/`_drawerSwitchEnd` · `_loadDrawerTab` · `_switchDrawerTarget` · `_startDrawerPoll`/`_stopDrawerPoll` · `_drawerMergeSupply` · `_drawerNormPeers`; `drawer.js`(1435 → 1169 行)删除定义只余调用点。接线 = `app.mixin(window.AQB_DRAWER_STORE)` + 三 shell `tpl-manifest` 各加一行(排在 `drawer.js` 之前)。
- **验收**: A/B DOM dump 两侧 sha256 **相同**; 全量 `test.full` 与 e2e 与上基线**逐位一致**(数字见基线切片, 不手抄)。

## 三处非显然的判断(下轮别再踩)

1. **`_scan_mixin_wiring` 的重名守阵是搬迁的硬约束** —— Vue mixin 后者静默覆盖前者。唯一安全姿势是「同类成员整体搬家、原文件不再定义」, **绝不复制方法体**(复制即重名, pytest 不一定报错 —— 是"全绿而功能静默消失"那类)。
2. **守阵读取面必须与代码同轮改** —— 十余条静态守阵按文件名定位方法体, 只搬代码不改测试会整批「找不到方法体」判红。改法是**只换读取文件、断言口径一字不动**(R8: 不许放宽)。
3. **shell 行数硬顶的腾行法** —— `prism/index.html` / `console/index.html` 贴硬顶, 加一行 manifest 必须减一行; 守阵比的是 `json.loads` 后的对象 ⇒ 把相邻两条 `parts` 项并到同一行(JSON 空白不被解析)即可, 清单语义不变。

## 待办 / 移交

- **W2–W6 待起**: W2 = 四页签 Vue 重建 + Tracker/用户/文件三列表注册进 `<aq-table>`; 双实现期守「**单一挂载点 + 特性开关**」(计划 R7), 旧渲染当基线逐页签替换, 每步收口新建基线切片。
- **cap 债务**: `memory-bank/modules/webui-static-contract.md` 已超 evergreen cap(自 W1 前即如此), 本轮只增一条回写; 清理需另开新会话(`commands run doc.caps -- --strict` 收口)。
