# 设置页程序化跳转的视图态被异步 hubRestore 复位冲掉

> 摘要: 程序化跳进设置页时同步设置的分区视图态, 会被 `cfgLoad` 完成后 `hubRestore -> hubGo` 的「进分区复位」路径冲掉 —— 跳转链必须 `.then` 在 `openSettings()` 之后
> 触发: openSettings, hubRestore, hubGo, 程序化跳转, 跳转后状态被复位, 覆盖层没打开, 自动展开失效, cfgLoad, kbGoSettings, transfer_flow
**Refs:** memory-bank/tasks/26-11-04-webui-hub-keys-merge.md

### 程序化跳转后「进分区复位」把同步先设的视图态冲掉 (2026-11-04 实测)

- **触发**: 代码化跳转「其它页面 → 设置页某分区并设置该分区的视图态」(如帮助浮层 `kbGoSettings` 跳 webui 卡并展开键位覆盖层, `hubGo("webui")` 后同步调 `kbFullOpenPanel()`), 而 `openSettings()` 是**先同步后异步**: `this.page = "settings"` 同步, 但首进设置页 `await cfgLoad()` 异步 —— 它成功后回调 `hubRestore()`, 恢复的视图若与本轮目标相同会**再走一遍 `hubGo(view)`**, 而各分区的 hubGo 分支带「进分区复位视图态」(webui 卡复位 `kbFullOpen`/`ctxCust.open`, hr_check 复位 `hrsOpen` 等), 把同步先设的状态覆盖回默认。跳转写成 `openSettings(); hubGo(...); setState(...)` 三连时必踩。
- **判别**: 真浏览器目检/探针才看得出 —— 页面落点正确(面包屑/分区都对)、控制台零报错, 但覆盖层/展开态没出现(模板 `v-show` 还是 false); 静态守阵与 e2e 运行期错误守卫都发现不了。时序上是「同步 setState → (稍后) cfgLoad resolve → hubRestore → hubGo 复位」。
- **处置**: 跳转链整体 `.then` 在 `openSettings()` 完成之后 —— `this.openSettings().then(() => { this.hubGo(view); setState(...); })`(`openSettings` 内部 await `cfgLoad`, 链上拿到时 hubRestore 已跑完)。**先例**: `shared/transfer_flow.js` 的「空态灰项 → 设置页 WebUI 卡」就是这条链; 本轮 `shortcuts_panel.js::kbGoSettings` 起初写成同步三连被目检抓到, 已改 .then。
- **守阵**: 无静态守阵(时序坑, 静态断言钉不住) —— 依赖目检脚本断言「跳转后覆盖层可见」; 复用此跳转范式的新入口(菜单/浮层跳设置页并预设状态)须真浏览器验证一次。
