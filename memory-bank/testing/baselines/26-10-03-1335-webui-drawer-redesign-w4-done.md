# 基线 · 2329 passed + 3 skipped / 99% —— WEBUI 抽屉重设计方案A W4(回归与验证)完结

> 摘要: 计划 26-10-03-0917 W4 波次(代码波): ①D3 窄屏降级落地 —— 视口 ≤900px 面板 fixed
> 全屏覆盖主区(!important 压内联高度记忆 / grip 隐藏 / statusbar 让位 / 关闭钮保留), 三皮肤
> 成对(atlas/console dialogs.css · prism views.css); ②W4 几何走查**非零改动** —— 真浏览器实证
> 停靠面板(sticky 吸底)盖住列表视口底部一段, 光标行滚到窗底被面板遮蔽(展开/收起/拖高三态全
> 中), 落 `_kbViewBottom()` 行可见下界单点(实测面板顶缘 - 8px 呼吸距; fixed 全屏态回落整窗高,
> 断点单点留在 CSS), `_kbViewportRow` 与 `_kbScrollRowIntoView`(渲染行 + 窗口化两路)改走该下界;
> ③前波移交观察项收口 —— trackers/peers 5s 轮询 tick 补种子视图可见性守卫(切走页面/视图不再对
> 隐藏面板拉取, 定时器不拆回页自恢复)。真浏览器: 自建走查单 24 项 × prism/atlas/console 全过
> (D3@900/@901 · 开面板 → 连发跟随 → Alt+2 → Esc 关面板 → 再 Esc 清筛选兜底 · 追剧/组行 kind
> 守卫与 Enter 语义 · 表头吸顶同步 · 搜索高亮 · 轮询收口); 仓库 `ui_smoke.cjs` prism+atlas
> 124/124、console 62/62 全绿 —— 前波在案的「末段 nav[1].click() 超时」本轮未复现(当前栈
> playwright-core 1.63 + chromium-1243, 判定 W2/W3 期间的栈版本漂移, 非回归)。
> Esc 层序走查在案: 面板开 + 帮助浮层开, 第一发 Esc 收面板、第二发收帮助(固定优先级序非 LIFO,
> 计划 §3.3 两层序之外的场景, 维持现状待编排者裁决)。
> 基线时间: 2026-10-03 13:35, feature/webui-drawer-redesign @ 工作区(W4 提交前, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2329 passed + 3 skipped / 99%**(13,433 语句 / 88 未覆盖 / 4,542 分支 / 89 partial,
test.full 28.48s, rc=0)。
相对上一切片(26-10-03-0913: 2325 passed + 3 skipped / 99%, 语句/分支数亦同) **passed +4**:
0a66c7c0(+1, 0746 认领链分隔符提示)+ 方案A W2/W3 两波(+2, test_drawer_dock_keyboard_w2 /
test_drawer_height_collapse_w3; W1 只扩 test_web.py 既有守阵断言不加条目)+ 本波
test_drawer_narrow_fullscreen_w4(+1: D3 三皮肤成对 / _kbViewBottom 单点与两处消费 /
轮询可见性守卫)。行为面变更由真浏览器走查单验证(72 断言全绿)。
