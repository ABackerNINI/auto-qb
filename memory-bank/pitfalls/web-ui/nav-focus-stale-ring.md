# 键盘切页后旧页签残留焦点框 (focus-visible 的 keydown 重估)

> 摘要: 鼠标点过的页签持有 DOM 焦点, 键盘切页(1/2/3)不动焦点; Chromium 在 keydown 分发时把焦点元素重估为 :focus-visible ⇒ 旧页签画出残留 outline。分发期间 matches(":focus-visible") 已翻转, **不能**用它区分焦点来源; 修复靠维护不变式(切页后导航焦点 == 活动页签, 否则 blur 归还 body), 单点 view.js::syncNavFocus。
> 触发: 键盘切页, 页签残留高亮框, 残留 outline, focus-visible, 焦点残留, 数字键切视图, 切页, tab 焦点, 修键盘导航, ESC 残留框, 按 Esc 多一个边框, 鼠标点击后按 Esc 出框, 焦点来源记账, modality
**Refs:** memory-bank/tasks/26-10-02-webui-nav-focus.md

### 键盘切页后旧页签亮框: 机制与修法 (2026-10-02 实测)

- **触发**: 修「键盘切页/快捷键切换后某元素残留高亮框」类报障; 或任何"鼠标聚焦的元素 + 后续键盘操作"组合的焦点类改动。
- **判别**: Playwright 状态读数三步定位 —— ①鼠标点元素: focused=true / `matches(":focus-visible")`=false / outline=none(正常); ②键盘操作(不移动焦点的全局键)后: 该元素仍 activeElement 且 fv 翻 true、computed outline 变 solid(残留框); ③根因确认 = 键盘路径**从不移动焦点**, 框来自浏览器 keydown 分发时对焦点元素的 fv 重估, 不是应用代码加了类。⚠ 关键陷阱: 在 keydown 处理器(含捕获级)里读 `matches(":focus-visible")` **已经翻转成 true**, 鼠标来源与键盘来源读数相同 ⇒ 想"识别焦点来源再决定保不保留焦点"这条路在分发期间根本不可行。
- **处置**: 不识别来源, 维护**不变式**: 切页/切视图后, 导航焦点要么恰在"新活动项"上(点击 / Tab+Enter 路径, 焦点保留, 不打断键盘 Tab 序), 要么 `blur()` 归还 body(鼠标遗留焦点)。DOM 身份用 `data-view` 类属性标识目标项(不靠 class——class 是响应式派生态)。本仓库单点: `view.js::syncNavFocus`(由 `goView` 调用) + `tpl/topbar.html` 三页签 `data-view`。**保留一项标准行为别"修"**: 按当前页自己的数字键(无视图切换)时, 焦点恰在活动页签上会按标准焦点语义显示框 —— 这是焦点位置与视图一致的正确状态, 抹掉它会伤键盘可达性。
- **守阵**: `e2e/views.spec.mjs`「导航焦点」双断言(双皮肤各一遍): 鼠标点页签持焦无框 / 键盘切页后旧页签不残留焦点框
  (2026-10-06 起由 e2e 轨道承载, 旧单页冒烟脚本已退役)。

### 复发(2026-11-19): ESC 后所有按钮类控件残留框 —— 焦点来源记账范式

- **触发**: 修「鼠标点按钮后按 Esc 多一个边框」类报障 —— 按钮类控件(主标签/主表表头/状态栏按钮/筛选器/设置/行语言/皮肤切换等)鼠标点击后按 Esc 出残留框; 或任何"鼠标遗留焦点 + 不移动焦点的全局键"组合。**为何没命中旧守阵**: 旧修法 `syncNavFocus` 只覆盖"数字键切页 + `data-view` 主标签", 触发键钉死 `1/2/3`、目标钉死 `nav.tabs [data-view]`; ESC 与其余按钮都不在那两条判据内, 直接绕过 ⇒ 同型机理复发。诊断别只盯旧页签, 先确认"任何鼠标遗留焦点 + 任意不移动焦点的全局键"都属同一机理。
- **判别**: 同旧条三步读数 —— 鼠标点元素 focused=true / fv=false / outline=none(正常), 按 Esc 后该元素仍 activeElement 且 fv 翻 true、computed outline 变 solid(残留框); 根因 = 键盘路径不移动焦点, 框来自 keydown 分发期 fv 重估, **不是**键帽显影 `kbd-reveal`(ESC 只移除该类、与 outline 无关)。分发期读 `matches(":focus-visible")` 已翻转为 true, 无法当场辨来源。
- **处置**: 在 **`focusin` 当场按 modality 记账**(此刻 fv 未被按键重估): 鼠标聚焦 fv=false 入账 `lifecycle.js::_mouseFocusEl`, 键盘 Tab 聚焦 fv=true 不入账。`_onEscKey` 退栈链**尾**(无条件, 不在 else-if 内)把仍是 activeElement 的鼠标遗留焦点 `blur()` 归还 body; 键盘焦点从未入账, 原样保留(不伤 Tab 序)。**配对守卫(评审 minor)**: 只记元素身份不够 —— 鼠标点按钮入账后若在同一元素按**实键**(焦点未移动、无新 focusin), modality 已转键盘、焦点框成标准语义, Esc 不该抹它; 补 `_onKeyModalityTrack`(非 Escape/非纯修饰键 keydown 清账), 修饰键(Shift/Ctrl/Alt/Meta)不清账、Escape 自身留给归还逻辑(注册在其后, 归还先跑)。**账面范式最易漏的边界**: 记账后必须有 modality 翻转的清账出口, 否则键盘可达性受损。
- **守阵**: `e2e/views.spec.mjs`「Esc 归还鼠标遗留焦点」(双皮肤)两类断言 —— 鼠标点控件→Esc 无残留框 / 鼠标点→End 转键盘 modality→Esc 焦点框保留; `tests/unit/test_webui_static_r4_poll_auth_lifecycle.py` 监听电池核注册/撤除对称(keydown 4→5 + focusin×1)与三 handler 记账语义。两条断言均做过红验(注掉对应 blur/清账即变红)。
