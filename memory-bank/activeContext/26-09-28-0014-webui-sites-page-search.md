# 站点页搜索实施(webui-sites-page-search)

> 摘要: 计划 26-09-27-1852 全部完结(96671860); 26-09-29 三方案拍板选 C 并已实施聚焦搜索层(档案 tasks/26-09-29-webui-tracker-focus-layer.md, 待提交)。
> 最后活动: 2026-09-29 04:20

## 已完成

- 搜索本体: config_hub.js(norm/parse/rows 单点 + computed 索引命中 + 单命中自动选中) · settings.html(搜索行/命中下拉/pill 去键数徽标) · config_editor.js(trackerQuery state) · console_hub.css(hb-tr-* 皮肤令牌样式)。
- 跳转器交互(2026-09-28 深夜): hubTrackerPick(点命中=选中+清词收层) + hubOnDocClick 点外即收(豁免 .hb-tr-search 行内点击); 原 Q5「保留搜索」随下拉形态退役; 守阵四条收起路径断言; 基线 26-09-28-2334。
- 档案与坑: tasks/26-09-28-webui-sites-page-search.md(子任务 7 条) + pitfalls/web-ui/overlays.md「形态切换要连交互一起重新评审」; 提交 96671860 已推 Gitee。
- 三方案重设计模板(2026-09-29 凌晨, 待拍板): 用户报四痛点(浮层覆盖突兀 / 无↑↓Enter / 命中数挤占搜索框 / 新增·导入与站点 pill 同形难分) → 出 [plans/26-09-29-0323-plan-webui-sites-search-3-proposals.html](../plans/26-09-29-0323-plan-webui-sites-search-3-proposals.html): A 就地过滤 / B 锚定面板 / C 聚焦搜索层, 全部真可操作样机(过滤+↑↓Enter+Esc+IME 守卫), 控制台皮肤令牌真值复刻。共通四条: 命中数移出输入框 / 全键盘 / 动作按钮形制分离 / `/` 聚焦搜索框(对齐 26-09-28-0354, 可剔)。真浏览器冒烟过(过滤 4/8、面板跳转器、聚焦层开合、375px 无横向溢出); harness 键盘事件管道不派发, ↑↓Enter 用页面内合成事件验证。
- 方案C 聚焦搜索层实施(2026-09-29 04:15, Done 待提交): 用户拍板选 C → 实施档案 [tasks/26-09-29-webui-tracker-focus-layer.md](../tasks/26-09-29-webui-tracker-focus-layer.md)。hub.trackerSearchFocus/trackerHitIdx + hubTrackerStageOpen/StageClose/Keydown 单点, 收层四路径(点命中/Esc/点暗幕/点外 .hb-tr-stage)一律清词; hubOnKey 增 IME 守卫; settings.html 聚焦层结构(面板三段式, 命中数/键位入面板头, 「新增站点「词」」入面板尾), pill 行尾动作区(hb-btn.dashed/ghost)分形; console_hub.css hb-tr-stage/veil/drop-hd/drop-list/drop-ft/cur + hb-btn.dashed + hb-pill-tail(三皮肤令牌共用, 暗幕字面黑与 shadow 家族同口径)。守阵 test_frontend_tracker_search_wiring 重写。真实 CSS 三态快照真浏览器目检过; 提交前合并远端 3 笔(HR v3 重建 05a8415, stash 腾挪零冲突)后新基线重测 **1736 passed + 3 skipped / 90%**(基线 [26-09-29-0415](../testing/baselines/26-09-29-0415-webui-tracker-focus-layer.md); 数字差来自远端 HR v3 守阵增删)。ship.commit 入库中。
