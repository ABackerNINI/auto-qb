# 1736 passed / 3 skipped —— 站点搜索改聚焦搜索层(方案C: 暗幕舞台 + 面板三段式 + 键盘导航)

> 摘要: 按 plans/26-09-29-0323 拍板(选 C)重做 trackers 搜索呈现层 —— 聚焦或有词即开层(暗幕 + 列表详情退隐 + 搜索行升面板), 命中面板三段式(命中数搬出输入框 / ↑↓ 活动高亮 + Enter / 「新增站点「词」」快捷新增), 新增/导入收进 pill 行尾动作区与站点 pill 分形; 收层四路径(点命中/Esc/点暗幕/点外)一律走 hubTrackerStageClose 清词单点, hubOnKey 增 IME 组词守卫。守阵 test_frontend_tracker_search_wiring 重写同步。纯前端, 增 0 测试仅重写断言。
> 基线时间: 2026-09-29 04:15(数字 04:35 在合并远端 05a8415 后的新基线上重测)

- test.full 一次通过: **1736 passed / 3 skipped**, 26.26s, TOTAL **90%**(12312 语句 / 1032 未覆盖 / 4172 分支 / 409 partial)。⚠ 与 26-09-28-2334 基线(1831/91%)的差来自**其间合并的远端 HR v3 重建**(be83d61 配置 40→14 键 + 守阵增删, 05a8415), 非本轮改动 —— 本轮增 0 测试仅重写 test_frontend_tracker_search_wiring 断言, 合并树上一次通过。
- 改动文件: shared/config_hub.js(状态/开合层/键盘/收层单点) · shared/tpl/settings.html(trackers 分支聚焦层结构) · shared/console_hub.css(hb-tr-stage/veil/drop 三段式/hit.act/cur/hb-btn.dashed/hb-pill-tail) · tests/test_web.py(守阵重写)。
- 视觉验证: 真实 CSS(console 皮肤 + console_hub.css)三态快照真浏览器目检通过 —— 闲置(行尾动作区与站点 pill 分形)/ 开层有命中(暗幕+升层面板+活动项左缘条+当前标记+快捷新增)/ 开层空态(语法引导)。
