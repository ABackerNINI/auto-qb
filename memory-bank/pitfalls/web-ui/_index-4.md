# web-ui — 前端 / WEB UI 纪律 · 卷 4/5

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `mixin-ce-inject-break.md` … `sticky-scrollpad-inset.md`(共 22 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [mixin-ce-inject-break.md](mixin-ce-inject-break.md) | 全局 mixin(CONFIG_EDITOR)给**每个**组件都挂 `provide(){ce:this}` + 空 cfg 树 —— 把根模板段头抽成中间层组件时, 若它不把注入到的 ce 原样透传, 插槽里的 hub-field 会注入到**该组件实例**: 字段恒显 sc… | Vue provide/inject, 全局 mixin, CONFIG_EDITOR, ce 透传, 插槽注入断裂, aq-fold, hub-field, 开关不显示磁盘值, 默认徽标, 设置页开关无效, 保存并应用不出现, 改配置重启… |
| [mixin-method-call-misses-methods-layer.md](mixin-method-call-misses-methods-layer.md) | `window.AQB_*` mixin 对象的方法嵌在 `.methods` 层下, 跨文件直调写根路径(`AQB_DECORATE.hrExclClass(...)`)时根对象无此键, 调用点每次执行必抛 `is not a function`; 模板绑定走 Vue mixi… | is not a function, hrExclClass, hrExclTip, AQB_DECORATE, methods 层, 根路径直调, 跨文件调用, mixin 全局对象, 每行渲染 TypeError, 判定门单点化, wi… |
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
| [rowwin-stale-rowh-pad-jump.md](rowwin-stale-rowh-pad-jump.md) | 行高逐行实测表 `_rowHs` 只在行渲染在场时更新 —— 行高变过且已滚出窗口的行存值永不修正; 窗口滑动越过它时 padTop 按陈旧存值超量替换, 渲染行整体跳 ±数px。e2e 像素级判据(T7 前置带 / S-A 公式落点)骑在漂移阈值边缘, 随机器环境两侧摆, 呈「… | 陈旧行高, 行高存值, 窗口滑动跳变, pad 超量替换, 内容跳数px, _rowHs, _measureRowH, 滚出窗口, 视觉跳变, 像素判据, 预热滚动, preheat |
| [scroll-visible-band.md](scroll-visible-band.md) | 键盘光标滚动跟随把「目标行几何在视口内」当成「看得见」, 但列表的上下边各压着一层随正文滚动的 chrome —— 顶部是吸在顶栏下缘的吸顶列头 `.group-head`(sticky, top = `--head-h - 1px`), 底部是固定状态栏 `.statusbar… | 键盘移到第一个种子只显示一半, 最后一个种子只显示一半, 翻页跳行, 翻一屏跳过行, PageDown 少看几行, 无光标回落, 跳极值行, 落回列表顶, 落到列表底, 追剧页键盘, 光标行被列头盖住, 光标行被状态栏盖住, 看不见当前行,… |
| [search-pending-collapse.md](search-pending-collapse.md) | 搜索匹配是服务端单点(search_torrents)、前端消费 searchHits 的模式下, "输入新词到响应返回之间沿用上一查询的命中集"(search-as-you-type)契约对「空集→首词」转换失效 —— 首词的待响应窗(防抖 400ms + 请求往返)里 sea… | 改搜索/筛选派生, 改 searchHits 消费, 新增走命中门的列表视图, 搜索时列表闪空, 搜索整页跳顶, 搜索时面板跳动, 待响应窗, search-as-you-type, filteredTorrents, filteredGr… |
| [search-views.md](search-views.md) | 搜索不是虚拟分组、负词种子级排除、脏标记是共享状态、鉴权不能靠"凭证串非空"、配置写盘按 BaseLoader 语义。 | 改搜索, 改视图脏标记, 改鉴权, 改登录, 改设置页, 改配置写盘, rid 门控 |
| [show-if-residual-key.md](show-if-residual-key.md) | schema 字段的 show_if 只控制「这一行渲染不渲染」; 用户把触发键从命中值切走后, 该字段先前写进树的值**仍留在配置树里**(show_if 不删键), 行又已隐藏 ⇒ 用户看不见也改不了, 保存时后端校验对残留键报错(如 watch_fields 仅在 trig… | 给规则/段字段配 show_if; 切走关联键后保存报"该键非法"; 字段在某取值下才合法 |
| [sortable-gate-source-split.md](sortable-gate-source-split.md) | 能力判据源分裂: 视觉侧硬编码 + 行为侧门控 = 「看着能点、点了没反应」的静默全灭 | 补门控, a11y 补课, headActivate, col.sortable, sortable, thead, 表头排序失效, 点了没反应, 视觉与行为分叉, 判据同源, 唯一调用方 |
| [stale-predicate-inverted.md](stale-predicate-inverted.md) | 同一对象上成对出现的 `active`(本图此刻该不该显示/拉)与 `stale`(在途响应是否**已过期**→丢弃)是**互为反义**的两个谓词; 机械改名/整行重写时把 `stale` 的 `!(...)` 敲成 `!!(...)`, 语义整个翻面 —— 恰在「本图正在被看」… | 改 stale 谓词, 机械改名, 双重取反, 图加载不出来, 一直显示正在加载, loading 不复位, 谓词极性, _qbLoad, _QB_SCOPES, active 与 stale |
| [sticky-scrollpad-inset.md](sticky-scrollpad-inset.md) | sticky 的视矩形被**滚动容器自身的 padding 内缩** —— top:0 实际停在 padding-top 之下、bottom:0 实际停在 padding-bottom 之上, 中途滚动时数据行文字从这两条缝里漏出来; 行级 grid 表格的吸顶列头与吸底汇总条会… | 吸顶, 吸底, sticky, 滚动容器 padding, drawer-body, 表头吸顶, 统计条吸底, 漏出文字, 行文字漏出, 顶部漏字, 底部漏字, 中途滚动, 未到顶, 没到底, dt11, 树表批量, drawer_tpl,… |
