# web-ui — 前端 / WEB UI 纪律 · 卷 3/4

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `injected-dom-title-migrated-to-aq-tip.md` … `sortable-gate-source-split.md`(共 26 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [injected-dom-title-migrated-to-aq-tip.md](injected-dom-title-migrated-to-aq-tip.md) | 全局自绘 tooltip 的「原生 title 断供式」机制(shared/ui_feedback.js 的 MutationObserver)对 **一切**新出现的 title 属性做单向迁移 —— 不只 Vue 模板渲染, **JS 手工插值出的 DOM(innerHTML… | 变体 DOM, title 属性, data-aq-tip, getAttribute null, [title] 选择器, MutationObserver, ui_feedback, 悬浮提示, Playwright title |
| [js-comment-terminator.md](js-comment-terminator.md) | JS 块注释以第一个 `*/` 结束 —— 注释文字里再出现 `*/`(如 `Key*/Digit*` 想表达通配前缀)会把注释提前砍断, 尾巴落成**代码态**; 与 CSS 版(见 css-comment-terminator)不同, 尾巴常能被解析成正则字面量等合法语法,… | 写 JS 注释, 注释里出现 星号斜杠, Digit is not defined, pageerror 白屏, node check 全绿, shortcuts.js |
| [kbd-cursor-collapse-dangling.md](kbd-cursor-collapse-dangling.md) | 收起展开态只复位展开态、不动 `kbCursor` ⇒ 光标仍指着已随收起卸载的明细行, 虚线框被宿主连坐带走, 观感是"锚点被清了" | Esc 收起, 展开态收起, 光标消失, kb-cursor 悬空, 明细行卸载 |
| [kbd-cursor-first-row-gap.md](kbd-cursor-first-row-gap.md) | 键盘光标首行虚线贴住吸顶列头: 行间有 gap 但首行与列头 0 间隙 | 光标虚线上边缘被遮挡, 第一个种子虚线, kb-cursor 上边被压, 首行贴着列头, 虚线缺一半, 键盘光标上边看不见, 三主表首行, torrents-dock group-table, padding-top |
| [kbd-range-view-scope.md](kbd-range-view-scope.md) | 成员行的 Shift+↑↓ 范围选择, `_kbExtend` 曾**一律**调 `shiftTorrentSel` —— 它的候选是**种子页平铺列表** `filteredTorrents`。在辅种页/追剧页该列表要么为空(懒加载, 未进过种子页)、要么与屏幕上的行无关, 于… | 键盘 Shift+↑↓ 选不中, 范围选中没反应, 辅种页/追剧页范围选择失效, shiftMemberSel, shiftTorrentSel, _kbExtend, filteredTorrents, 成员行范围, 选中集合不增长, 选… |
| [kbd-row-kind-dispatch.md](kbd-row-kind-dispatch.md) | `shortcuts.js` 的键盘动作大量按 `c.kind` 分派(group / show / ep / torrent)。把一种新行种纳入 `_kbRows()` 光标链时, 只在**新增那一条链**上接线(如"成员行能 ↓ 走到""成员行能 Shift 扩选"), 而同… | 新增行种/成员行入光标链, 改 `_kbRows` 或任一 `_kb*` 动作, 快捷键按了没反应, 收起当前行不生效, 光标进组后 ← 无效, kind 分派漏分支 |
| [kbd-tab-set-sync.md](kbd-tab-set-sync.md) | 详情面板的页签快捷键(Alt+1~5)与**可见页签集合**是两套独立事实源 —— 页签栏收敛为合并页签后, 注册表五档仍按旧的四页签映射(`Alt+3` 名义「用户页」实际落到收起页签), 症状是**按了键切到别的页签**(不报错、不白屏, 只是"怎么跳到这页去了")。修法 =… | 改页签/子视图集合, 页签栏收敛或增删页签, 快捷键切错页签, Alt+数字不对, 合并页签, 快捷键没同步, 按了跳到别的页 |
| [layout-css.md](layout-css.md) | 行宽口径、表头吸顶、两表逐栏对齐、sticky 层叠、flex 挤压、flex 子项错行、特异性之争、状态色分不出 —— 前端版式类的固定判据。 | 改 CSS, 布局, 表格, 滚动条, 表头吸顶, sticky, flex, flex-basis, 对齐, 未对齐, 没对齐, 错行, 文字高低不一, 后者更高, 统计栏, 工具条, 图例, align-items, stretch,… |
| [mixin-ce-inject-break.md](mixin-ce-inject-break.md) | 全局 mixin(CONFIG_EDITOR)给**每个**组件都挂 `provide(){ce:this}` + 空 cfg 树 —— 把根模板段头抽成中间层组件时, 若它不把注入到的 ce 原样透传, 插槽里的 hub-field 会注入到**该组件实例**: 字段恒显 sc… | Vue provide/inject, 全局 mixin, CONFIG_EDITOR, ce 透传, 插槽注入断裂, aq-fold, hub-field, 开关不显示磁盘值, 默认徽标, 设置页开关无效, 保存并应用不出现, 改配置重启… |
| [modal-mask-click-self-drag.md](modal-mask-click-self-drag.md) | `.modal-mask` 上写 `@click.self="closeX"` 判的是 click 事件的 target, 而 click 由 mousedown 与 mouseup 的**公共祖先**派发(DOM 规范)—— 在对话框里的输入框按下左键拖选文字、鼠标终点落到遮罩… | 遮罩关窗, click.self, 拖选文字窗口消失, 拖选后弹窗自己关了, mouseup 公共祖先, 点空白关窗误判, mousedown 起手位置, 添加种子窗口消失, 弹窗误关, text selection, 拖拽抬手 |
| [modal-width-tier.md](modal-width-tier.md) | 弹窗宽度档位与内容形态错配: 编辑框骑通用基档, 长值被输入框裁掉 | 弹窗太小, 对话框太小, 重命名弹窗, modal 宽度, 宽度档位, --modal-w-base, --modal-w-add, rename-dialog, 输入框裁掉, 长名显示不全, 种子名显示不全, 弹窗宽度档, cls 附加类… |
| [nav-focus-stale-ring.md](nav-focus-stale-ring.md) | 鼠标点过的页签持有 DOM 焦点, 键盘切页(1/2/3)不动焦点; Chromium 在 keydown 分发时把焦点元素重估为 :focus-visible ⇒ 旧页签画出残留 outline。分发期间 matches(":focus-visible") 已翻转, **不能*… | 键盘切页, 页签残留高亮框, 残留 outline, focus-visible, 焦点残留, 数字键切视图, 切页, tab 焦点, 修键盘导航 |
| [opacity-tier-ghosting.md](opacity-tier-ghosting.md) | 深色底 + 两排高度相似的路径文本(当前位置/目标位置只差一两级目录)时, 给上排 `opacity:.55` 做「暗/亮」分层, 远看不会被读成层级, 而是被读成下排文字的半透明残影(近视错觉)。层级要靠**形状差异**(删除线/标签), 不能靠亮度差; 尤其别在等宽 11px… | 双排显示, 保存路径, 整组迁移, relocate, rel-pair, rel-pa, opacity, 颜色浅, 伪影, 重影, 近视错觉, 淡影, 深色底, 层级, 删除线, 斜体, row_lang.css, D6 |
| [overlays.md](overlays.md) | 弹层 / 浮层 / 遮罩 / 多选与命令回执 —— "点了没反应"这类症状的固定排查顺序; 含浮层几何(视口钳位 / 尺寸估算)与 Esc 退栈顺序。 | 浮层, 弹层, 右键菜单, 遮罩, 点了没反应, 多选, 命令回执, 强制汇报, 起点, anchor, Shift 连选, 落起点, selAnchor, 视口钳位, 菜单高度, 溢出视口, 菜单项点不到, outside of the… |
| [password-autofill-dirty.md](password-autofill-dirty.md) | 密码框的浏览器自动填充会凭空写脏配置树 | 有改动还没保存, 一进设置就脏, 自动填充, autofill, 密码框, 密码管理器, autocomplete, new-password, 脏标记凭空变真, 配置树被写 |
| [perf-cadence.md](perf-cadence.md) | 主循环节拍、缓存边界、埋点与相对时间 —— 改热路径 / 改节拍 / 加埋点前必读。 | 性能, 热路径, jsonable_encoder, 节拍, 刷新, 轮询, 缓存, 埋点, 相对时间, 时间列, yapf |
| [poll-reseed-filter.md](poll-reseed-filter.md) | 数据是轮询/增量刷新、某一组筛选的**候选值从数据派生**(不是定长常量数组)时, 若在每次数据到达的派生函数里直接 `选中集.add(候选)`, 每轮刷新都会把用户刚取消的勾选加回来 —— 表现是「这一组筛选器每隔 N 秒自动重置」; 而候选是定长常量的那几组(形态 / iss… | 筛选器自动重置, 过滤器自己复位, 每隔一会儿又全选, 勾选取消了又回来, 轮询后筛选失效, 派生候选 vs 常量候选, 只有某一组筛选出问题, 状态筛选器重置, poll reseed, auto-reselect, 筛选器刷新重置, 筛… |
| [progress-bar.md](progress-bar.md) | `.m-progress` 是 flex 行 —— 条 `flex: 1 1 auto` 吃剩余空间, 右侧百分比 `.val` 只占自身文本宽, 「100.0%」比「5.2%」宽 ⇒ 同列各行条的长度/起点随文本宽逐行漂移。处置 = **数值盒** `min-width: 4e… | 改进度条, 进度条长度不一致, 条宽漂移, 条长不一致, m-progress, 进度列, 数值盒, flex 条宽, 百分比文本 |
| [reannounce-inactive-gate.md](reannounce-inactive-gate.md) | 「非活跃种子不允许强制汇报」这条 qB 对齐规则, 三处最容易做错 —— ①**判定读 `kind` 而不读 qB 原始 `state`**: `kind` 现 7 档(error/checking/paused/downloading/seeding/**moving**/ot… | 强制汇报, reannounce, 非活跃, 暂停种子, 排队种子, 搬迁中, moving, queuedDL, stoppedUP, checkingResumeData, is-gated, 置灰, 按钮变灰, 右键置灰, qB 口径… |
| [row-shadow-zeroed-by-rowlang.md](row-shadow-zeroed-by-rowlang.md) | 皮肤 CSS 给行加 box-shadow 会被 row_lang flat 归零 | 行高亮不生效, box-shadow 无效, 右键目标不可见, row_lang, ctx-src |
| [rowh-sig-and-transition-geometry.md](rowh-sig-and-transition-geometry.md) | 行高签名混入视图态因子 + 容器过渡期几何不可采信: 千级下切页/关抽屉秒级卡死 | 切标签页卡死, 关抽屉卡死, 能滚不能点, 行高签名, viewMode, ResizeObserver, _winCtnSync, 假 bump, 全量量齐 |
| [scroll-visible-band.md](scroll-visible-band.md) | 键盘光标滚动跟随把「目标行几何在视口内」当成「看得见」, 但列表的上下边各压着一层随正文滚动的 chrome —— 顶部是吸在顶栏下缘的吸顶列头 `.group-head`(sticky, top = `--head-h - 1px`), 底部是固定状态栏 `.statusbar… | 键盘移到第一个种子只显示一半, 最后一个种子只显示一半, 翻页跳行, 翻一屏跳过行, PageDown 少看几行, 无光标回落, 跳极值行, 落回列表顶, 落到列表底, 追剧页键盘, 光标行被列头盖住, 光标行被状态栏盖住, 看不见当前行,… |
| [search-pending-collapse.md](search-pending-collapse.md) | 搜索匹配是服务端单点(search_torrents)、前端消费 searchHits 的模式下, "输入新词到响应返回之间沿用上一查询的命中集"(search-as-you-type)契约对「空集→首词」转换失效 —— 首词的待响应窗(防抖 400ms + 请求往返)里 sea… | 改搜索/筛选派生, 改 searchHits 消费, 新增走命中门的列表视图, 搜索时列表闪空, 搜索整页跳顶, 搜索时面板跳动, 待响应窗, search-as-you-type, filteredTorrents, filteredGr… |
| [search-views.md](search-views.md) | 搜索不是虚拟分组、负词种子级排除、脏标记是共享状态、鉴权不能靠"凭证串非空"、配置写盘按 BaseLoader 语义。 | 改搜索, 改视图脏标记, 改鉴权, 改登录, 改设置页, 改配置写盘, rid 门控 |
| [show-if-residual-key.md](show-if-residual-key.md) | schema 字段的 show_if 只控制「这一行渲染不渲染」; 用户把触发键从命中值切走后, 该字段先前写进树的值**仍留在配置树里**(show_if 不删键), 行又已隐藏 ⇒ 用户看不见也改不了, 保存时后端校验对残留键报错(如 watch_fields 仅在 trig… | 给规则/段字段配 show_if; 切走关联键后保存报"该键非法"; 字段在某取值下才合法 |
| [sortable-gate-source-split.md](sortable-gate-source-split.md) | 能力判据源分裂: 视觉侧硬编码 + 行为侧门控 = 「看着能点、点了没反应」的静默全灭 | 补门控, a11y 补课, headActivate, col.sortable, sortable, thead, 表头排序失效, 点了没反应, 视觉与行为分叉, 判据同源, 唯一调用方 |
