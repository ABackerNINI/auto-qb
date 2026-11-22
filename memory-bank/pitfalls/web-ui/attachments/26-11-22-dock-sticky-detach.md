# dock-panel · 列表变短致 sticky 吸底脱锚

> 摘要: 列表被搜索/筛短后文档变矮、sticky 停靠面板脱锚上浮的机理、真机逐帧取证、撑满首屏处置与守阵, 含 2026-11-14 边距生命周期口径更新。
> 触发: 搜索筛选, 查面板跳动, sticky 脱锚, min-height, 真机逐帧采样, 滚动几何

### 列表变短 = 文档变矮: sticky 吸底脱锚, 面板跟着内容末尾走

- **触发**: `.drawer-dock` 是流内 sticky 吸底元素, 「钉在视口底」只在**自然落点低于视口下界**时生效
  —— 列表被搜索/筛选筛短(或真 0 命中落空态)后文档变矮, 面板脱锚上浮到内容末尾; 列表长短一变,
  钉住/脱锚两态之间切换就是用户看到的"面板跳动"。视口越高跳幅越大(800px 视口 14px, 线性放大)。
- **判别**: 采样面板 `getBoundingClientRect().top` 贯穿整个交互: 搜索/筛选前后 top 变了 = 脱锚
  (内容列高度问题); top 恒定但背景列表跳 = 滚动钳制(结果确实变短, 属预期)。注意「调用存在但
  几何/时机错」静态守阵探不到, 必须真浏览器逐帧采样(dock-panel 2026-10-04 回归同教训)。
- **处置**: 让内容列(`.layout`)恒撑满首屏: `min-height: calc(100vh - var(--head-h))`(顶栏实测高
  走 `columns.js::_syncHeadHeight` 既有单点, **不写死** —— 顶栏随媒体查询/状态条/窄屏折行变高)。
  内容列恒撑满则面板自然落点恒在视口底, sticky 恒生效, 锚点与列表长短无关。三皮肤成对改
  (atlas/console 的 components.css + prism 的 views.css)。
- **守阵**: `tests/test_webui_static_skins_widget.py::test_frontend_search_pending_no_collapse`(三皮肤 .layout min-height 锚)+
  `e2e/drawer-dock-stability.spec.mjs`(行为: 搜索全程面板 top 偏差 ≤2px)。配套根因(待响应期
  塌列表)见 search-pending-collapse。
- **取证(2026-10-07)**: 修复前短列表态面板 top 416 vs 钉住态 430; 修复后三皮肤逐帧采样零变化。
- **2026-11-14 口径更新(26-11-12 抽屉专题 T6, `fbf5dc26`)**: enter 边距生命周期重构后
  (margin-top 退出 JS, 总占位 = margin CSS 恒 8 + height, enter 零凹陷/leave 单段式),
  enter 全程 docH 单调不减、leave 单段式收拢 —— 旧口径里「贴底钳制属预期」的逐帧反复形态
  结构性消失; close 期 −8 残差同根消失。钳制语义只剩「结果确实变短后的一次性」这一种。

**Refs:** memory-bank/tasks/26-10-07-webui-drawer-search-jump.md
