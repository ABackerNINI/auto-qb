# 26-09-25-webui-page-location-persist — 设置页刷新会回到种子页

**Status:** Done
**Added:** 2026-09-25
**Updated:** 2026-09-25
**Summary:** 用户报"设置页刷新会回到种子页"。根因: 顶层 `page` 与设置分区 `hub.view` **都是纯内存态**(`page` 初值恒 `"groups"`) ⇒ F5 必掉回辅种页 + 设置首页, 编辑到一半的位置全丢。修法: 两个位置都按"用户意图"落盘(键 `autoqb.ui.page` / `autoqb.ui.hub`, 与既有 `autoqb.ui.view`/`autoqb.ui.theme` 同族), 读侧**白名单**(只认 `"settings"`, 不信任存储内容), 写侧**单漏斗**(`persistUiPage()` + `hub.view` watcher)。**关键第二处**(只改初值不够): 设置页配置树是**按需加载**的(`cfgLoad` 只在 `openSettings`/页内"重试"里调) ⇒ 启动路径必须在 `startPolling()` 尾部补一次 `cfgLoad()`(它是两条登录路径的唯一汇合点, 鉴权已放行), 否则首屏停在「配置加载失败 + 重试」而 `page` 值看着完全正确。恢复的分区 key 由 `hubRestore()`(cfgLoad 成功后)对 **schema 校验**(分区随版本改名/删除)并复用 `hubGo()`(trackers/rules 默认选中项与日志/HR 懒加载都在那条路径里)。纯前端改动(3 个 shared 片段文件, 两套 UI 共用 ⇒ 一次改两处生效), 后端零改动零新路由。守阵: `test_web.py::test_frontend_page_location_persisted`(三处红验)+ `ui_smoke.cjs` 场景「设置页刷新保持位置」(双 UI, **已红绿双验** —— 缺陷版实测复现 `刷新后 page=groups, hub=hub, schema=false`)。全量 **1601 collected: 1600 passed + 1 skipped** / TOTAL **91%** 不变 / sidefx 越界 0; 冒烟双 UI 各 **46 项 0 失败**。
**Topics:** webui-page-location-persist

## 原始请求

> 修复问题: 设置页刷新会回到种子页

## 思考过程与决策

### 根因: 位置是纯内存态, 刷新即重建 Vue 实例

`shared/app.js` 的 `data()` 里 `page: "groups"` 是**唯一**的页面状态, 没有任何持久化;
`shared/config_hub.js` 的 `hub.view: "hub"` 同理。刷新 = 新 Vue 实例 ⇒ 两个都回默认。
对照既有先例: `viewMode` 早已落盘(`autoqb.ui.view`, `initialViewMode()`), 所以这属于**漏做**, 不是设计取舍。

### 形态取舍: localStorage 而非 URL hash

- **localStorage(采用)**: 与既有 UI 意图同族(`autoqb.ui.view` / `autoqb.ui.theme`), 改动最小;
  两套 UI(`/prism/` 与 `/atlas/`)共用同一 origin ⇒ 位置也自然共享(两套 UI 的页面拓扑相同, 语义正确)。
- **URL hash / `pushState`(否决)**: 能顺带支持浏览器前进后退与书签, 但本仓**零 hash 路由**,
  引入等于新开一条架构线(还要处理与两套 UI 目录路由的关系), 与"修一个报障"的粒度不匹配。

### ❗只改初值不够: 按需加载的页面必须在启动路径补一次加载

设置页的 `cfg.schema` 只在 `cfgLoad()` 里赋值, 而 `cfgLoad()` 的调用点只有 `openSettings()` 与页内「重试」。
若只把 `page` 初值改成读存储, 刷新后确实停在设置页, 但渲染的是 `v-else-if="!cfg.schema"` 那条分支 ——
**「配置加载失败 + 重试」**。这个坑的隐蔽点: 症状看着像"持久化没生效", 而 `page` 值完全正确。
落点选 `startPolling()` 尾部 —— 它是**两条登录路径**(本机免鉴权 / 密钥验证通过)的唯一汇合点, 到那儿鉴权已放行。
守阵因此必须**同时**断言"page 对"与"数据已加载", 只断言 `page` 会漏(已写进 pitfalls)。

### 恢复的分区 key 必须对 schema 校验

读 localStorage 发生在**模块加载期**, 那时 schema 还读不到 ⇒ 只能"先取值、后校验": 校验放在 `cfgLoad()`
成功之后(`hubRestore()`)。不校验的后果是升级后分区改名/删除 → 刷新停在**空白分区**, 页面上没有任何提示。
采用时**复用 `hubGo()`** 而不是自己重设字段: 懒加载(`__logs` 拉日志 / `hr_check` 拉站点状态)与
trackers/rules 的默认选中项都在那条路径里, 重写一遍必漏一半。

### 命名: 不能叫 persistPage

`columns.js` 已有 `persistPage(page)`(列状态唯一漏斗), 而前端是**十几个 mixin 注入同一实例**、
同名**静默覆盖**。新方法定名 `persistUiPage()`(机检 = `test_frontend_static_bundle_health` 第 10 项)。

## 实现计划

| # | 文件 | 改动 |
|---|---|---|
| 1 | `src/auto_qb/webui/static/shared/app.js` | `initialPage()`(白名单读 `autoqb.ui.page`)+ `data().page` 改走它 + `watch(page)` 调 `persistUiPage()` + `startPolling()` 尾部补一次 `cfgLoad()` + 新增 `persistUiPage()` 方法 |
| 2 | `src/auto_qb/webui/static/shared/config_hub.js` | `initialHubView()`(读 `autoqb.ui.hub`)+ `hub.view` 初值改走它 + 新增 `watch: "hub.view"` 落盘 + 新增 `hubRestore()`(schema 校验 + 复用 `hubGo`) |
| 3 | `src/auto_qb/webui/static/shared/config_editor.js` | `cfgLoad()` 成功后调 `this.hubRestore()`(schema 到手那一刻才校验得了分区 key) |
| 4 | `tests/test_web.py` | 新增 `test_frontend_page_location_persisted`(静态钉 4 件事) + 头部「## 测试计划」补一行 |
| 5 | `scripts/ui_smoke.cjs` | 新增场景「设置页刷新保持位置」(真实手势: 点设置 → 进分区 → reload; 四项断言) |

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 三个 shared 片段的位置持久化实现 | Done |
| 静态守阵 1 条 + 测试计划 docstring 同步 | Done |
| 守阵三处红验(watch 落盘 / 启动补 cfgLoad / schema 校验) | Done |
| 冒烟场景 1 条(双 UI) + **缺陷版红验**(复现 `page=groups`) | Done |
| 全量测试(test.full 1600+1 / TOTAL 91% 不变) | Done |
| 知识库回写(webui-static-contract / pitfalls 新主题 / baseline / 档案 / 切片 / 走查清单) | Done |
| 顺路发现的问题入池(刷新丢未保存改动) | Done —— `issues/26-09-25-1702-bug-webui-settings-unsaved-changes-lost.html`(已实测取证) |
| 提交 / 推送 | **待用户显式指令**(本轮只到"修复 + 验证") |

## 进度日志

- 2026-09-25 16:4x 开工。`git fetch gitee develop` 后本地 HEAD == 远端 `8598f49`, 工作区干净 ⇒ 无需同步。
- 定位: `page` 与 `hub.view` 均无持久化; `cfgLoad` 只在 `openSettings`/「重试」调用(⇒ 启动补加载是必须的第二处)。
- 实现 1–5 项。`node --check` 三个改动文件通过; 行尾保持 CRLF(全仓一致, 新增行未混入 LF)。
- 静态守阵首跑红: 我的正则漏了 `re.M`(app.js 是 CRLF, `^` 锚点没生效) ⇒ 补 `re.M` 后绿。**注意**: 该守卫的
  `watch(page)` 正则必须带 `re.M`, 否则恒 None(已固化进守阵)。
- 三处红验(逐条摘掉再跑): 摘 `persistUiPage()` 调用 → 红; 摘 `startPolling` 的 `cfgLoad` → 红;
  摘 `hubRestore` 的 schema 校验 → 红。绿恢复。
- 冒烟: `ui_harness.py --torrents 300 --port 8155` + `ui_smoke.cjs`。**缺陷版红验**(`git show HEAD:` 回退三个文件)
  ⇒ 新断言实测 FAIL, 读数 `刷新后 {"page":"groups","hub":"hub","schema":false}` —— 与用户报障逐字对应;
  恢复修复版后 prism **46 项 0 失败**、atlas **46 项 0 失败**, 新断言读数
  `进入/刷新后 均 {"page":"settings","hub":"basic","schema":true,"crumb":"常规","store":"settings|basic"}`。
- 全量: `commands run test.full` ⇒ **1601 collected: 1600 passed + 1 skipped**(+1 = 本轮守阵) / TOTAL **91%**
  (10949/789/3598/325, 与上一版逐项相同 —— 本轮无 .py 源码变更) / sidefx 越界 0。
  ⚠ 直接 `export TMPDIR=… && uv run pytest` 会多出 2 条红: `test_kb_index_is_regenerated` 与
  `test_kb_index_and_files_are_bijective` —— 那是**新建 pitfalls 主题后未重建索引**的预期红, `kb.index` 后转绿。
- 知识库回写: `modules/webui-static-contract.md` 补「UI 位置持久化」条; **新建**
  `pitfalls/web-ui/ui-location-persist.md`(三条判据: 启动补加载 / schema 校验 / 漏斗命名查重);
  `testing/baseline.md` 顶部 1599→1600; 走查清单补一条; 档案(本文件) + 切片 + `kb.index` 重建。
- 2026-09-25 17:0x 用户指令「"设置页有未保存改动时刷新会丢改动"提个 issue」⇒ 入池
  `issues/26-09-25-1702-bug-webui-settings-unsaved-changes-lost.html`(bug / standard)。为让接手人不必重查,
  用 `ui_harness.py --port 8156` + 真 chromium **实测复现**并贴原文读数: 改动后 `dirty=true` 而服务端
  `null`(只活在内存) → F5 后回原值 + `dirty=false`, 全过程 `dialogs=0`(零确认框)。
  ⚠ **顺带修了 create-issue skill 的模板缺陷**: 两个 `assets/issue-*.html` 缺 `doc-topic`
  (doc-forms 约定要求 issue 必须带), 导致**任何新建 issue 都会撞** `test_docs_forms.py::test_issue_topics_present`
  —— 模板补 `{{TOPIC}}` + `new_issue.py` 加 `--topic`(默认 = slug) + SKILL.md 记该参数与"不可省"的理由。
