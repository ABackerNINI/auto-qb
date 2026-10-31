# 3129 —— WEBUI 抽屉重构 W0 冻结基线 + W1 数据层抽离(26-10-11-2106 计划)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html

> 摘要: 计划 `memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html`(专题 `webui-drawer-refactor`)的 **W0 + W1**。用户「按推荐实施」= 拍板点 D1/D2/D3/D4 一律取推荐项 **A**(Vue 3 组件重建 · 收敛为声明式密度变体 · 按页签分波替换 · 三列表注册进 `<aq-table>`)。**W0**(零代码, 冻结契约与验收基线): 记现状 `test.full` 与全量 e2e 数字 + 建「抽屉 DOM dump」临时探针(打开种子详情 → 逐页签 + 回常规, 双皮肤共 10 项, 归一易变位后取 sha256)作后续每一步的 A/B 对照。**W1**(数据层抽离, 零观感变化): 把取数 / 竞态 / 等待集合 / 软切换序号从 `shared/drawer.js` 剥成 `shared/drawer_store.js`(`window.AQB_DRAWER_STORE`, 与渲染无关的一层), **方法体逐字未改、只换落点**。验收: 真浏览器 A/B DOM dump **逐字节等价**(两侧 sha256 相同) + `test.full` 与 e2e 与基线**逐位一致**。
> 基线时间: 2026-10-11 21:36

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 到 `d7c5b351`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3129 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16517 语句 / 151 未覆盖 / 5626 分支 / 134 partial; 本轮 31.49s, `test.full` 总 33.5s)
- **与上基线(26-10-11-2040)逐位相同** —— 这正是 W0/W1 的验收口径(W1 是零观感变化的纯搬迁, 不许有任何数字漂移)。

## e2e 实测

- 命令: `commands run dev.e2e`(Windows; 桩 `scripts/ui_harness.py` 由 webServer 自动起, 默认档 ok/on/on/300)
- **实测 (Windows)**: **158 passed + 0 failed + 10 skipped**(4.2m)—— 与上片基线逐位一致。
- **W0 点名的四支 spec 逐支通过数**(逐支单跑 = 全量任务的入参收窄到单个 spec 路径, 机制见 `commands run dev.e2e` 的 note; 合计 **38 passed**, 与静态枚举 6+8+10+8+6 逐支对齐):
  `drawer-groups-shows.spec.mjs` 6 · `drawer-merge.spec.mjs` 8 · `column-prefs.spec.mjs` 10 ·
  `kbd-members.spec.mjs` 8 · `kbd-scroll-band.spec.mjs` 6(双皮肤各半)。

## DOM dump A/B(「渲染逐字节等价」判据)

- 探针: 打开种子详情面板 → 逐页签(Tracker/用户/内容/常规)+ 回常规, 取 `.drawer-dock` `innerHTML`,
  归一 40 位 hash / 大小速度单位 / 时长 / 时刻 等易变位; 双皮肤各 5 项 = **10 项**。
- **A 侧(改动前)= B 侧(改动后), `sha256 = e4b8c224a9e9fc5a49dce58343f7442be61dc9ad7ccd40b9415edfb689e6a1f8`**
  (dump JSON 也逐字节相同)。这是 W1「零观感变化」的硬判据。
- 探针是**临时件**, 收口已移出 `e2e/`(留 `tmp-analysis/drawer-dump-probe.spec.mjs` 备复用; `tmp-analysis/` 已 gitignore),
  故不影响 e2e 用例计数。方法可复用: 同一 spec 两次跑, 换 `DUMP_OUT` 落盘后 diff。

## 增量明细(本轮真正新增)

- **源** —— 新增 `webui/static/shared/drawer_store.js`(`window.AQB_DRAWER_STORE.methods`, 收 `_fetchDrawerDetail|Trackers|Files|Peers` · `_drawerLoadSeq`/`_drawerStale` · `_drawerWait`/`_drawerWaitSources`/`_drawerDone` · `_drawerBusyArm|Disarm`/`_drawerSwitchEnd` · `_loadDrawerTab` · `_switchDrawerTarget` · `_startDrawerPoll`/`_stopDrawerPoll` · `_drawerMergeSupply` · `_drawerNormPeers`); `drawer.js` 相应删除这些定义(1435 → 1169 行, 只剩调用点); `app.js` 加 `app.mixin(window.AQB_DRAWER_STORE)`; 三份 `tpl-manifest` 各加一行 `/shared/drawer_store.js`(排在 `drawer.js` 之前; prism/console 贴 210 行硬顶, 压相邻两条 `parts` 项腾行, 解析后清单不变)。
- **测试** —— `test_web_shortcuts.py` 三处、`test_webui_static_dom_panel.py` 五处用例的读取面从 `drawer.js` 改到 `drawer_store.js`(断言口径一字未改, 只换读哪个文件); 无新增/删除用例。
- **文档面** —— 计划 `26-10-11-2106-*`(doc-status Open → In Progress + §05 进度行 + §09 拍板结论 + §11 变更记录) + 任务档案 `26-10-11-webui-drawer-refactor.md` + 本切片 + `activeContext/26-10-11-2136-webui-drawer-refactor.md` + `modules/webui-static-contract.md`(抽屉数据层落点回写)。

## 风险 / 观察

- **`_scan_mixin_wiring` 的重名守阵是搬迁的硬约束**: 新 mixin 的成员名与其它片段不得重名(Vue mixin 后者覆盖前者, 静默)。W1 的做法是「同类成员整体搬家、原文件不再定义」, 故无重名; `test_frontend_drawer_tpl_registry_wiring` 的 `dt*` 全仓无重名检查仍绿。
- **接线守阵看的是「文件被清单引用 + 被 app.mixin 注入」**, 不看它是不是组件 —— `drawer_store.js` 走 `app.mixin` 即满足; 三皮肤 `tpl-manifest` 必须逐项相等(`test_frontend_template_split_wiring`), 故三份同改。
- **守阵读取面搬迁必须与代码同轮**: 若不改测试, 15+ 条断言会因「drawer.js 里找不到方法体」整批判红 —— 已同轮改(R8 口径: 不许放宽, 只换读取文件)。
- W2–W6 待起(W2 = 四页签 Vue 重建 + 三列表接入 `<aq-table>`; 双实现期须「单一挂载点 + 特性开关」, R7)。
