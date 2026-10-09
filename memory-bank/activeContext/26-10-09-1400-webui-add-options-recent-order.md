# 添加种子三候选「最近使用」排序 · 已闭环

> 摘要: 用户命题「WEBUI 添加种子时, 保存路径/分类/标签按最近使用排序」。先出两方案对比(由种子记录派生 vs 本机手动选择历史)供拍板 —— 用户选**方式一(由种子记录派生)**, 兜底 = 从未用过落末尾按字母序。实现: `add_torrent.js` 新增模块级纯函数 `_addOrderByRecent`(时间降序 → 未用过按字母序, `slice()` 不改入参)与 `_addNormPath`(与后端 `infra/utils.path_normalize` 同口径), 时间表 `_addRecencyMaps` 取自**跨视图自取数单点** `_addRecencyRows`(与 filters.js::facetRows 同族), `loadAddOptions` 三候选在落袋处统一过排序单点。**e2e 首跑当场抓出一个真缺陷**: 首版直读 `state.torrents`, 而 `/api/state` 按 `VIEW_ARRAYS` 裁剪 —— 默认辅种页只回 groups + singles ⇒ 时间表恒空、排序静默退化成字母序(即 pitfall「跨视图的常驻消费者」复发)。同轮按用户指派改桩数据面(分类/标签候选 + 每对独立 save_path + 组键归真机口径)并新增真浏览器 e2e。零后端端点改动 / 零新增持久化 ⇒ 多端天然一致、不受「清站点数据」影响。
>
> 最后活动: 2026-10-09 14:19

**Refs:** memory-bank/pitfalls/web-ui/contract-api.md,memory-bank/modules/webui-static-contract.md,memory-bank/testing/browser-env.md,memory-bank/testing/baselines/26-10-09-1419-webui-add-options-recent-order.md

## 本轮完成

- **需求拍板(先对比后动手)**: 两种「最近使用」判定依据逐项对比(数据源 / 近期口径 / 多端一致 / 新增存储 / 规则赋值 / 清站点数据 / 改动面), 用户选**由种子记录派生**; 未用过**排末尾并按字母序**。
- **实现(纯前端, 零后端端点改动)**: `add_torrent.js` —— 模块级 `_addOrderByRecent(options, recency)` 与 `_addNormPath(p)`; 方法 `_addRecencyRows()`(跨视图取数) + `_addRecencyMaps()`(三张 `Map<值, 最近 added_on>`); `loadAddOptions` 三个 pick 不再各自 `.sort()`。口径 = 该值下 `added_on` 最大值降序 → 未用过(0)落末尾 → 同时间按 `localeCompare`; 表空一律退化纯字母序(与旧行为逐字一致, 候选未到位时零观感差异)。
- **两处静默失效(本件真正的坑, 都是"不报错不白屏")**:
  - ①**路径口径**: `/api/paths` 回的是**已归一**路径, 而取数行的 `save_path` 是 qB **原文** ⇒ 必须过 `_addNormPath` 才能命中, 否则时间表恒不命中。
  - ②**跨视图裁剪**: 添加入口是顶栏常驻, 而 `/api/state` 按 `VIEW_ARRAYS` 裁剪阵列(默认辅种页只回 groups + singles) ⇒ 直读 `this.torrents` 恒空。修法 = 取数面单点 `_addRecencyRows`(种子页平铺 / 其余 `singles ∪ decoratedGroups[].members`), 判据同 `pitfalls/web-ui/contract-api.md`「跨视图的常驻消费者」(**本条复发第 4 次**, 已在该条记"为什么没命中")。
- **桩服务数据面(用户指派)**: `FakeClient` 补 `categories` 字段(默认空, 既有用例行为不变); `ui_harness.py` 新增 `_inject_add_options` 灌分类/标签候选、合成种子**每对独立 `save_path`**(组内一致 / 组间互异)、组键由假键 `(name, ())` 改为真机口径 `(save_path, ())` —— 后者顺带修掉"全库种子名被灌成『保存位置』候选"与 `open-path(group)` 去开一个名字的失真。
- **守阵**: 静态 `tests/test_webui_static_dom_panel.py::test_frontend_add_options_recent_order`(node 电池真跑两纯函数 + 静态钉接线 / 时间表 / 跨视图三支); 真浏览器 `e2e/add-options-recent-order.spec.mjs`(@fast, 双皮肤, 期望序由**桩同源公式现算**, 钉分类与标签全序 + 路径头部)。
- **红验**: ①副本上把比较方向变异(`tb - ta` → `ta - tb`)⇒ node 电池多项转红(降序 / 未用过落末尾 / 部分命中 / 大时间戳); ②把 `_addRecencyRows` 临时退回 `this.torrents` ⇒ 双皮肤 e2e 双双转红(分类序退回字母序), 还原后全绿。

## 待办 / 移交

- 无代码遗留; 回写随本专题入库。
- 立档阈值仍未命中(单源文件 + 无计划/报告制品) ⇒ 只写本切片, 不建 `tasks/` 档案。
- **未做**: Linux(WSL)侧未重测(仅 Windows 单侧采样, 与近期基线同口径)。
