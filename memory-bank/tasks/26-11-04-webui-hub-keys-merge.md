# 26-11-04-webui-hub-keys-merge — WebUI 快捷键设置并入 WebUI 卡与双折叠改版

**Status:** Done
**Added:** 2026-11-04
**Updated:** 2026-11-04
**Summary:** 快捷键设置从独立「keys」卡并入「WebUI」卡(展开即全屏覆盖层), 快捷键块与右键菜单布局块默认折叠; grilling 三轮定案后实施, 静态守阵 + e2e 全量 + 真浏览器目检全绿
**Topics:** webui-hub-keys-merge
**Refs:** memory-bank/testing/baselines/26-11-04-0112-webui-hub-keys-merge.md

## 原始请求

1. 「WEBUI将快捷键设置移入WebUI设置中」—— 设置首页的独立「快捷键」卡删除, 键位编辑并入「WebUI」卡。
2. 「快捷键设置于右键菜单布局设置都默认折叠」—— 两块进分区时默认收起。
3. 「grilling后实施」—— 先 grill 定案再动代码。

## 思考过程与决策

grilling 三轮, 关键拍板:

- **D1 双脏状态编排(原 Q3)**: 用户先倾向 B(统一进全局 actbar 单一保存按钮); 经缺点分析(半保存状态/放弃粒度变粗/切分区守卫不对称/`cfgGuardActive` 必须扩双源)后, 用户改拍**全屏覆盖层方案** —— 键位块展开 = HR 站点状态同款全屏覆盖层, 物理盖住配置树 actbar, 任一时刻视野里只有一个保存按钮; 键位独立草稿状态机原样保留, B 案的缺点全部蒸发。`cfgGuardActive` 扩双源(cfgDirty || kbDirtyView)是 B 案遗产中仍然必做的(键位脏时 F5 不能静默丢失)。
- **D2 折叠形态(原 Q2/Q10)**: 快捷键 = 折叠块 ⇄ 全屏覆盖层(无内嵌展开态, hrsOpen 同款); 右键菜单布局 = 行内折叠(运行日志同款, `v-if` 卸载折叠体); 两块展开态均不持久化, 进分区回折叠。跳检开关与种子转移目标不折叠。
- **D3 关闭守卫(原 Q8/Q9)**: 覆盖层 ✕/ESC/点遮罩三路都走 `kbFullClose`, 未保存确认「放弃并关闭/留在面板」, 确认后回滚再关(草稿生命周期跟展开态绑定); 覆盖层内保存成功留在面板(不自动关)。
- **D4 帮助浮层入口(原 Q4)**: 「前往设置自定义」→ webui 卡 + **自动展开**覆盖层。
- **D5 细节**: 首次展开才拉 `/api/keys`(运行日志/HR「首次展开才拉」先例); 旧 localStorage `"keys"` 存量值经 `HUB_VIEW_ALIAS` 取值处单点映射成 `"webui"`(D13 先例); 首页 WebUI 卡读数并入键位段(三段拼接)。

## 实现计划

1. `settings-detail.html`: 删 `hub.view === 'keys'` 分支; webui 分支加快捷键折叠块 + `aqb:kb-full-modal` 覆盖层(必须 `.hb-blk` **兄弟**, clip-path 坑); 右键菜单布局块头加展开/收起 + `v-if="ctxCust.open"`。
2. `config_hub.js`: 删首页 keys 卡; WebUI 卡读数/lede 并入快捷键; `hubNow` 删 keys 分支; `HUB_VIEW_ALIAS` 加 `keys: "webui"`; `hubGo` 删 keys 分支、webui 进分区复位 `kbFullOpen`; 新增 `kbDirtyView` 计算属性。
3. `shortcuts_panel.js`: `kbFullOpenPanel/kbFullClose/kbReadout`; `kbGuardLeave` 改 webui 口径(`view !== "webui" || target === "webui" || !kbFullOpen || !kbDirty`); `kbGoSettings` 链在 `openSettings().then()` 之后(hubRestore 复位竞态, 见坑档)。
4. `lifecycle.js` Esc 退栈链 + `dialogs_meta.js` escBusy + `shortcuts_engine.js` `_kbOverlayBusy` 三处名单同步 `kbFullOpen`。
5. `config_editor.js`: `cfgGuardActive` 扩双源; `cfgReloadGuard` 「保存并刷新」补存键位(失败内部已回滚)。`state.js`: 双 watcher(`cfgDirty`/`kbDirtyView`)都传 `true` 让 `cfgGuardActive` 重算(传各自新值会摘掉还需要的兜底)。
6. `ctx_menu_custom.js` `cmPanelEnter` 复位 `ctxCust.open`; `console_hub_panels.css` 加 `.hr-full-modal-acts`(共享层单点, 免四皮肤成对改)。
7. 守阵: `test_web_shortcuts_drawer.py` 重写 `test_settings_panel_section` + 新增 `test_kb_full_overlay_wiring`; `test_webui_static_dom_page_layout.py` watcher 断言改双源; e2e `ctx-custom.spec.mjs` 适配默认折叠。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 模板改版(settings-detail.html 三块) | Done(2026-11-04) |
| 2 | config_hub.js 卡片/映射/分支 | Done(2026-11-04) |
| 3 | shortcuts_panel.js 覆盖层方法与守卫 | Done(2026-11-04) |
| 4 | ESC 三处名单同步 | Done(2026-11-04) |
| 5 | 刷新兜底双脏源 | Done(2026-11-04) |
| 6 | CSS 与折叠复位 | Done(2026-11-04) |
| 7 | 守阵 + e2e 更新 | Done(2026-11-04) |
| 8 | 验证: test.quick/test.full/e2e 全量/真浏览器目检 | Done(2026-11-04) |

## 进度日志

### R0 · 立档 + 实施 + 验证 (2026-11-04)

grilling 三轮定案(D1-D5)后一次实施完成。验证: `test.quick` 先红 1 条旧 watcher 守阵(钉死单源旧形态), 已同步双源判据后全绿; e2e 全量冒烟零红; `test.full` 全绿, 基线见 `commands run kb.baseline`(切片 26-11-04-0112)。真浏览器目检(atlas/flux 双皮肤): 折叠态摘要正确、覆盖层铺满中段盖住 actbar(elementFromPoint 探针命中 modal)、Esc 关闭/录制态 Esc 不关覆盖层、帮助浮层跳转自动展开。目检抓到并修复一个真 bug: `kbGoSettings` 同步设展开态会被 `cfgLoad`→`hubRestore`→`hubGo` 的「进分区回折叠」竞态冲掉, 改链在 `openSettings().then()` 之后(transfer_flow.js 同款先例), 已记坑档(`pitfalls/web-ui/webui-settings-jump-async-restore.md`)。

- 2026-11-04 01:15 grilling 三轮定案后实施: 快捷键设置从独立 keys 卡并入 WebUI 卡(展开即全屏覆盖层), 快捷键/右键菜单布局默认折叠; 刷新兜底扩双脏源; 守阵重写+e2e 适配+目检抓到并修复 hubRestore 复位竞态(kbGoSettings 链 openSettings 之后); test.full 全绿基线切片 26-11-04-0112
