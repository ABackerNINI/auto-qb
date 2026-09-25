# 26-09-25 WebUI 设置页位置持久化 (page / hub.view)

> 摘要: 用户指令「修复问题: 设置页刷新会回到种子页」—— 顶层 `page` 与设置分区 `hub.view` 都是纯内存态 ⇒
> F5 必掉回辅种页 + 设置首页。已修完并验证(3 个 shared 片段 + 静态守阵 + 冒烟场景, 双 UI 已红绿双验),
> **未提交**(等用户显式说"提交")。关键第二处: 只改初值不够, 设置页配置树按需加载 ⇒ `startPolling()` 尾部
> 必须补一次 `cfgLoad()`, 否则首屏停在「配置加载失败 + 重试」而 `page` 值看着是对的。
> 触发: 设置页刷新, 回到种子页, 页面位置, page 持久化, hub.view, initialPage, persistUiPage, hubRestore
> 最后活动: 2026-09-25 16:57

## 状态

**代码 + 守阵 + 验证全部完成, 未提交。** 全量 `test.full` **1601 collected: 1600 passed + 1 skipped** /
TOTAL 91% 不变; 冒烟双 UI 各 46 项 0 失败; 缺陷版红验复现 `刷新后 page=groups, hub=hub, schema=false`。

## 本轮完成

- **`shared/app.js`**: `initialPage()`(白名单读 `autoqb.ui.page`)· `data().page` 改走它 ·
  `watch(page)` 调 `persistUiPage()` · `startPolling()` 尾部补一次 `cfgLoad()` · 新增 `persistUiPage()`。
- **`shared/config_hub.js`**: `initialHubView()` · `hub.view` 初值改走它 · 新增 `watch: "hub.view"` 落盘 ·
  新增 `hubRestore()`(对 schema 校验 + 复用 `hubGo`)。
- **`shared/config_editor.js`**: `cfgLoad()` 成功后调 `hubRestore()`。
- **守阵**: `tests/test_web.py::test_frontend_page_location_persisted`(三处红验)+ 测试计划 docstring 一行;
  `scripts/ui_smoke.cjs` 场景「设置页刷新保持位置」(双 UI, 缺陷版红验)。
- **知识库**: `modules/webui-static-contract.md` 补条; 新建 `pitfalls/web-ui/ui-location-persist.md`;
  `testing/baseline.md` 1599→1600; 走查清单 +1; 档案 `tasks/26-09-25-webui-page-location-persist.md`。

## 下一步

1. **等用户显式说「提交」** 才走 `ship.commit` / `ship.push`(本轮指令是"修复问题", 不含提交授权)。
2. 用户真机走查: 在设置页(任意分区)按 F5 / 重开浏览器, 确认仍停在原分区(走查清单已登记)。
3. ⚠ 未做(不在本次范围, 已入池):
   `memory-bank/issues/26-09-25-1702-bug-webui-settings-unsaved-changes-lost.html` ——
   刷新会**丢失未保存的配置改动**(`cfg.tree` 是内存态, `cfgDirty` 时无 `beforeunload` 提醒);
   已实测取证(零确认框 + 刷新后回原值), 与本轮"位置"是两个问题。

## 关键判据(避免重踩)

- 位置落盘**只改初值不够** —— 按需加载的页面必须在启动路径补一次加载, 且守阵要同时断言"数据已加载"。
- 恢复的、由 schema 定义的 key 必须**先取值后校验**(模块加载期读不到 schema)。
- mixin 片段里新方法名先查重(`persistPage` 已被 columns.js 占用, 同名静默覆盖)。
