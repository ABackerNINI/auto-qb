# 键盘切页后旧页签残留焦点框 (focus-visible 的 keydown 重估)

> 摘要: 鼠标点过的页签持有 DOM 焦点, 键盘切页(1/2/3)不动焦点; Chromium 在 keydown 分发时把焦点元素重估为 :focus-visible ⇒ 旧页签画出残留 outline。分发期间 matches(":focus-visible") 已翻转, **不能**用它区分焦点来源; 修复靠维护不变式(切页后导航焦点 == 活动页签, 否则 blur 归还 body), 单点 view.js::syncNavFocus。
> 触发: 键盘切页, 页签残留高亮框, 残留 outline, focus-visible, 焦点残留, 数字键切视图, 切页, tab 焦点, 修键盘导航
**Refs:** memory-bank/tasks/26-10-02-webui-nav-focus.md

### 键盘切页后旧页签亮框: 机制与修法 (2026-10-02 实测)

- **触发**: 修「键盘切页/快捷键切换后某元素残留高亮框」类报障; 或任何"鼠标聚焦的元素 + 后续键盘操作"组合的焦点类改动。
- **判别**: Playwright 状态读数三步定位 —— ①鼠标点元素: focused=true / `matches(":focus-visible")`=false / outline=none(正常); ②键盘操作(不移动焦点的全局键)后: 该元素仍 activeElement 且 fv 翻 true、computed outline 变 solid(残留框); ③根因确认 = 键盘路径**从不移动焦点**, 框来自浏览器 keydown 分发时对焦点元素的 fv 重估, 不是应用代码加了类。⚠ 关键陷阱: 在 keydown 处理器(含捕获级)里读 `matches(":focus-visible")` **已经翻转成 true**, 鼠标来源与键盘来源读数相同 ⇒ 想"识别焦点来源再决定保不保留焦点"这条路在分发期间根本不可行。
- **处置**: 不识别来源, 维护**不变式**: 切页/切视图后, 导航焦点要么恰在"新活动项"上(点击 / Tab+Enter 路径, 焦点保留, 不打断键盘 Tab 序), 要么 `blur()` 归还 body(鼠标遗留焦点)。DOM 身份用 `data-view` 类属性标识目标项(不靠 class——class 是响应式派生态)。本仓库单点: `view.js::syncNavFocus`(由 `goView` 调用) + `tpl/topbar.html` 三页签 `data-view`。**保留一项标准行为别"修"**: 按当前页自己的数字键(无视图切换)时, 焦点恰在活动页签上会按标准焦点语义显示框 —— 这是焦点位置与视图一致的正确状态, 抹掉它会伤键盘可达性。
- **守阵**: `scripts/ui_smoke.cjs`「导航焦点」双断言(双 UI 各一遍): 鼠标点页签持焦无框 / 键盘切页后旧页签不残留焦点框。
