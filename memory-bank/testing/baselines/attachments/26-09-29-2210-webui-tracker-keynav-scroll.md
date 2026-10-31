# 基线 · 1751 passed + 2 skipped —— 站点搜索滚动跟随修复轮 (键盘活动项 scrollTop 差值)

> 摘要: issue 26-09-29-2142(命中列表 max-height 300px 超出后 ↑↓ 无滚动跟随)修复轮 ⇒ hubTrackerKeydown
> 改 idx 后 $nextTick 调新增 hubTrackerScrollActIntoView(getBoundingClientRect 差值手动调 scrollTop,
> block:"nearest" 语义; 不用 scrollIntoView —— 逐层滚祖先会连带滚暗幕后面的整页); 程序滚动可能补发的
> 合成 mousemove 由同日已修 hubTrackerHoverIdx 3px 门限挡掉, 不复发闪烁。守阵
> test_frontend_tracker_search_wiring 扩 4 断言(②b)。
> 基线时间: 2026-09-29 22:10 (develop @ 4ecd222b, 开工前 commands run my-commit-flow.sync 已同步)
> 档案: tasks/26-09-29-webui-tracker-focus-layer.md

TOTAL 1751 passed + 2 skipped / 91%(12442 语句 / 999 未覆盖, test.full 30.35s, rc=0) —— 0 failed。
数字与上轮切片 26-09-29-2145 完全一致 —— 本轮 = 1 个新 JS 方法 + keydown 1 行挂接 + 既有守阵函数
并入 4 断言, 不增用例数。改动面: config_hub.js / tests/test_web.py。
