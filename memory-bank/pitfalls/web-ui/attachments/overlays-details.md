# 浮层与交互的完整处置与实测证据 — 外迁详情(原 `pitfalls/web-ui/overlays.md` 段落原文)

> 摘要: `pitfalls/web-ui/overlays.md` 的详细处置/实测证据原文外迁(主档为控 cap 原位留指针); 判据与实测证据原样保留。
> 触发: 同主档 `pitfalls/web-ui/overlays.md` 的触发词(完整列表见主档头部)。

> 本文件是**外迁存档**: 主档该段原文一字未改搬来 (仅相对链接整体下移一层 —— 本文件在 `pitfalls/web-ui/attachments/`); 本目录不计 cap, 主档原位留指针。
## 浮层能透出下方正文: 先查「该皮肤的表面令牌带不带 alpha」, 不是 blur 没写好

- **处置**: 浮层底一律改用不透明兜底令牌 `--bg-pop`(flux `#1c2a3f` = `--bg-elev` 覆在页底 `--bg` 的等效色), **不要加 blur**
  (预算守阵 `_FLUX_BACKDROP_BUDGET` 会红)。shared 层浮层(console_hub/row_lang)在 flux 侧用 `html[data-fx-preset]` 前缀覆盖,
  不动 shared 本体(否则波及 atlas/prism/console)。口径见 conventions/webui.md「浮层不透明兜底」段。
- **反向坑(2026-11-03 复发形态): 「找回毛玻璃」别做成删/加 blur 或把弹窗底统一成近不透明** ——
  `.modal` 的 `backdrop-filter` 一直都在, 丢的是**透视度**: 底从 `--bg-card`(.82)换成 `--bg-elev`(.92)后
  blur 只剩 8% 透视, 肉眼读作毛玻璃消失。判别 = 计算样式 `background-color` alpha 是否 ≥ .9; 处置 = 让
  挂 blur 的表面用半透明角色底(`--msg-base: var(--bg-card)` 只挂 `.modal-mask`), 无 blur 浮层继续 `--bg-pop`,
  **不要**为了找效果去新增 backdrop-filter(预算钉死)。守阵 `_scan_flux_modal_frost`(双向钉弹窗 blur+半透明底
  与 `--bg-pop` 不透明底)。

## 全屏遮罩错误浮层无 dismiss 路径 = 整页操作锁 ≤ 轮周期

- **处置**: 遮罩退栈**最上档** + Esc 即收 (照 webui 26-10-06 口径: 退栈 order = visual z-order, 遮罩先于被盖住的层, 否则 Esc 穿过遮罩关被盖的**不见**层); 遮罩档判用 `hidden` 现 (屏幕上能看见的东西同名)。
  - kb.nav 已修 (26-10-13-0434): `escRetreat()` 单点链里 overlay 档 (`hideError()`) 排先于 ctxMenu/drawer 档; 守阵 `test_esc_closes_overlay_first` 钉 (链档序 + CSS z 序同视觉层叠)。

## 浮层"点了没反应"首先查**定位祖先**

- **处置**: 排查法 —— 打 `getBoundingClientRect()` 看坐标。

## "聚焦即展开"的输入框必须同时 `@click.stop`

- **处置**: 面板根节点加 `@click.stop`。

## 弹层"左对齐 + 固定宽度"在靠右锚点上会伸出视口

- **处置**: 打开弹层的**同一同步调用栈**里测 `anchor.left + 菜单宽 > innerWidth - 8` 并加 `flip-x`。
  ⚠ 注意 `ev.currentTarget` **只在 handler 同步代码内有效**。

## 浮层钳位不能用**常量**估算高度 —— 菜单高度随分支差一倍, 下部锚点的底部项点不到

- **处置**: ①钳位拆两跳: `_menuPos` 只出**初值**, 开层后按 `offsetWidth/offsetHeight` **实测**
  重钳位(`ui_feedback.js::_menuFit`), 量测放 `$nextTick` —— Vue 补丁后、浏览器绘制前, 故不产生
  可见跳位; ②watcher 单点收口(开层入口有六处, 直挂方法必漏), 且判据要用**对象替换**
  (`this.X = {…}`)而非 `visible` 翻转 —— 否则"菜单还开着又右键另一行"漏钳位(右键不触发 window
  的 click 收层); ③菜单比视口还高(极矮视口)才顶到上缘 + `max-height` 可滚: 常态挂 `overflow`
  会把 `position:absolute` 的 flyout 次级面板一起裁掉, 且每次开层要先复位 `maxHeight`;
  ④测试侧钉 **e2e**: 这类几何缺陷 pytest 跑不出来, 而 arrange **挑上部行**只是对冲、会把缺陷藏住
  —— 判据 = 挑**下部**锚点, 断言菜单盒 `y+height <= innerHeight - 8` **且**真实点击底部那一项。
  守阵: `test_webui_static_dom_panel.py::test_frontend_ctx_menu_refit_by_measured_size`(接线) +
  `e2e/menus.spec.mjs` 的 CTX-fit 用例(几何 + 真实手势; issue 26-10-06-1717)。

## Esc 退栈顺序 = 视觉层叠顺序(z-index), 不是打开先后 —— 两图同开时按层高关

- **处置**: 链序按视觉层叠排(弹层 130 > 抽屉 80 ⇒ `historyOpen` 分支先于 `drawerVisible`)。
  `dialogs.js::escBusy` 是"有没有层"的布尔(顺序无关), 不受影响, 无需改。守阵:
  `test_webui_static_dom_panel.py::test_frontend_qb_traffic_chart_wiring` 里加 `hist_at < drawer_at` 的**顺序**断言
  —— 只断言"分支存在"漏得掉顺序错(这正是本坑逃过守阵的原因)。

## 无遮罩浮层的三个细节

- **处置**: 根节点 `@click.stop`; 选项用 `@mousedown.prevent`; 原生 `<datalist>` **必须整体退役**。

## 形态切换要连交互一起重新评审 —— 分栏语境的「保留搜索」移植到覆盖式浮层 = 死锁

- **处置**: 覆盖式浮层的收起按「选中即收 + 点外即收」设计, 收层一律清词(不引入 dismissed
  状态位, 显隐仍由词驱动); 形态切换提交前自问「原布局下每个交互在新形态下还成立吗」。
  守阵: `test_web_backend_misc.py::test_frontend_tracker_search_wiring`(四条收起路径)。

## 不可见的全屏遮罩会拦掉整页点击

- **处置**: 加固 —— `<transition :duration="200">` + `.xx-leave-active { pointer-events: none }`。

## flyout 次级菜单: hover 规则会连子面板一起染色 / 只挂 mouseenter 就永远不收

- **处置**: ① `.ctx-item:where(:hover) > .ico`(`>` 限直接子级 + `:where()` 把 :hover 特异性压到 0,
  与语义色规则同重并按源码顺序让位); ② 收起挂**父项**的 `mouseleave`(mouseleave 只在离开父项
  **及其全部后代**时触发 ⇒ 父项↔面板互切不会误收; 面板上再挂一条 mouseleave 反而会在
  "从面板回到父项"时误收, 因为父项不会再收一次 mouseenter), 面板自身只挂 `mouseenter` 撤销挂起的收起;
  ③ 延迟 ~180ms 收起, 一级菜单关闭时撤销挂起的定时器。守阵: `test_webui_static_dom_panel.py::test_frontend_ctx_submenu_single_entry_and_hover_close`。

## 删除编排在前端而非后端

- **处置**: 保持这个边界; 想在后端加复合命令要先推翻这条设计。

## 多选保留策略: 增量刷新后按 key/hash 交集保留选中

- **处置**: 三条一起实现, 缺一条会出现"选中莫名消失"或"批量命令报 404"。

## 右键菜单的"目标"必须由**选中集合**决定, 不能只看被点的那一行 (CTX-03)

- **处置**: ①在 `open*Menu` 里算 `menu.multi`(见 `menu.js::_ctxMulti`, 复用 `_bulkTargets` 判"在不在集合里");
  ②模板加一条 `v-if="menu.multi"` 批量分支, 动作**整份复用批量浮条的链路**(`ctxAct`→`bulkAct` /
  `ctxDelete`→`bulkDelete`), 不自己再拆一遍目标集合(虚拟行/组展开/失效目标跳过三条语义都在 `_bulkTargets` 里);
  ③**每个 `open*Menu` 都要写 `multi`** —— 三视图共四个入口(组/成员/剧/集), 漏一个那条路径就静默退回单目标。
  ❗`ctxAct`/`ctxDelete` 必须**先收起菜单**: 菜单根节点是 `@click.stop`, 全局"点空白关闭"接不到。
  ❗批量菜单里不放单目标项(详细信息/限速/重命名/导出/复制): 它们对 N 个目标没有明确语义。
  守阵: `test_webui_static_dom_panel.py::test_frontend_ctx_menu_multi_select_targets_selection` + 冒烟 CTX-03 六条(双 UI)。

## 起点(anchor)与光标(focus)是两件事; 点击落起点的写入必须排除 Shift

- **触发**: 改 Shift 区间选择 / 改多选起点 / 实现"点击落起点"这类键鼠衔接(2026-10-02 计划
  26-10-02-0608 实测); 2026-10-19 用户报障「Shift 连选后按 Esc, 光标指向最后一个选择的种子,
  但再次 Shift 连选不以光标为起点」(猜测 Esc 错清锚点 —— 只对一半, 见 ③)。
- **判别**: 光标(`kbCursor`, 每按一次 ↑↓ 就变)与起点(`selAnchor*`, 一次扩展手势内**必须不动**)
  是两个独立语义 —— 合并成一个字段(报告 26-09-30-1806 的方案 C)会让 Shift+↓ 连按只能选相邻两行。
  三处容易写错的约束:
  - **① 写入位置与 Shift 守卫**: 约束「写在修饰键分支**之前**」与约束「**不写** Shift 分支」只能靠
    `if (!event.shiftKey) this._selSetAnchor(...)` 同时满足。**无条件早写**会让 Shift+点击把起点
    重置到目标行 ⇒ 区间塌成单行(计划 §07.1 的 M1「点第 5 行 → Shift+点击第 20 行 = 选 5–20」
    退化成只选第 20 行)。**判据**: 计划正文的"实现约束"与验收表的**行为口径**冲突时, 以验收表为准
    —— 约束条目常漏掉守卫条件, 验收表才是用户可感知的语义。
  - **② 键盘先落起点再移动光标**: `_kbExtend` 必须 `_selSeedAnchorFromCursor()` → `_kbMove(delta)`,
    顺序反了光标已移走 ⇒ 起点解析取到**新**光标, 区间同样塌成单行。
  - **③ 鼠标先落起点再改写光标**(2026-10-19 补; 计划当年漏掉的第三处, 与 ② 同祸): 鼠标五入口
    (`onGroupClick` / `onMemberClick` / `onTorrentClick` / `onShowClick` / `onShowEpClick`)第一行
    历来是"落光标", Shift 分支里才解析起点 —— 锚点缺失时兜底链的「当前光标」一环读到的是
    **刚点的行** ⇒ 区间塌成单行。锚点缺失的两条来路: Esc 退栈链兜底 `clearSelection()`
    (`lifecycle.js`)把 `selAnchor*` 连同选中一起清(**清锚点是选中状态语义, 不是缺陷**; 方案 B
    法则 3 本就走光标兜底), 以及全新会话首次 Shift。修法 = 入口在改写 `kbCursor` **之前**、
    Shift 限定地调 `_selSeedAnchorFromCursor()`, 与键盘 `_kbExtend` 同纪律。**判据**: 凡
    "先改 focus 再读 anchor"的顺序都与 ② 同祸, 与输入通道无关。
- **处置**: 起点解析/写入收成单点(`selection.js` `_selAnchor` / `_selSetAnchor`, 兜底链
  显式锚点 → 当前光标 → [group: 展开的组] → 列表首行), 消掉"四处消费者各写一遍 `list[0]`"的漂移源;
  落起点**只写 `selAnchor*`**, 不碰 `selGroups`/`selMembers`(普通点击仍不选中)。
  `_selSeedAnchorFromCursor` **逐 kind(group/member/unit)试落** —— `_selContext` 只回当前视图
  主 kind(辅种页恒为 group), 单 kind 落点覆盖不到成员行的 member kind(辅种页成员行 Shift 手势
  同根取不到原点, 2026-10-19 一并收编)。
  守阵: `tests/test_web_shortcuts_cursor.py::test_shift_anchor_unified`(五入口 seed 调用位于 kbCursor
  改写之前且限 Shift; 落点覆盖 member/unit kind; `_kbExtend` seed 先于 `_kbMove`) +
  e2e `e2e/shift-select-anchor.spec.mjs`(2026-10-19, 双皮肤 @fast: 种子页"Esc 后 Shift 连选以
  光标为起点"原报场景 + 辅种页成员行同根场景 + 无 Esc 常规路径回归; 已做红验 —— 回退修复后
  前两条双皮肤 4 红、回归条不误红)。

## 命令回执机制: `cmd_id` 的生成与剔除

- **处置**: 加新元数据键时同步 drain 的过滤名单。

## 强制汇报的"成功"回执是 **tracker 确认**而非 API 返回

- **处置**: 改这条链路时先补齐替身字段, 否则测的是空壳。

（关联件见头部 **Refs:** 行 —— 原段内 **Refs:** 是其子集, 2026-10-31 随重复声明守卫收敛删除）
