# 变体表格体整帧换清宿主子树后滚动容器 scrollTop 现算落 0 —— 缺成对恢复即列表跳

> 摘要: 变体表格体整帧换清宿主子树后滚动容器 scrollTop 现算落 0 —— 缺成对恢复即列表跳
> 等级: L0
> 触发: 点击跳动, 列表跳, 整列表位移, 滚动位落 0, 整帧换, replaceChildren, withScroll, scrollTop 现算, 滚到中间再点后跳, 数据回路重拉后跳, rerender 单点重渲后跳, 瞬态自回位, 0.x 秒后回位, CSS 动画重播, 入场动画重播, anchFill 摘插锚, 锚保活, page-in, 长生命周期元素, 逐帧采样
**Refs:** memory-bank/tasks/26-10-14-webui-content-click-jump.md

## 条目

### 变体 10/11 整帧换缺 withScroll (26-10-14 三复查「点击跳动」, 已修)

- **触发**: 用户报「点击跳动(点击引发行位移/重排)」; 或任何变体整帧换清宿主子树后滚动位跳.
- **判别**: 症状即整列表 scrollTop 跳后点击走数据回路(setFilePriority 到 _editPost 到 _fetchDrawerFiles 到 _dtNotify 到 rerender 到 replaceChildren). 行身份 ref-stable(_dtMergeRows 写字字段, 不重建) —— 位移即滚动位, 不行重建.
- **处置**: 整帧换收进 H.withScroll(host, ...) —— 01-09 变体同口径成对恢复单点 helper. withScroll 记 scrollTop/scrollLeft 宿主父(.drawer-body) 帧换前, 恢复后.
- **守阵**: 既有 dt-live-update #8 check-no-jump 仍绿(本修不改列集/几何/交互件).
- **家族关系**: 同族「整帧换清滚动宿主后需成对恢复」—— 凡整帧换清滚动宿主都要问「滚动位落 0 后回?」. 新写整帧换时先 grep withScroll, 别手写恢复算式.
- **复发**: 1 —— 26-10-14 四复查用户仍报跳动: 本条修法(withScroll 缺口收)未命中真机形态, 桩内 scrollTop 本就无偏移(harness 证明); 真根因为 CSS 动画重播(见下条), 与本条的滚动位现算**是两条不同的位移路径**, 别互相顶罪.

### 长生命周期表格体 anchFill 摘插锚 = CSS 入场动画重播 (26-10-14 四复查「点击跳动, 持续 0.x 秒后回位」, 已修)

- **触发**: 用户报「点击跳动, 持续 0.x 秒后回到原位」—— **瞬态自回位**是关键特征; 或任何「长生命周期元素被摘下再插回」后该元素的 CSS 入场动画重播.
- **判别**: 与上条(滚动位现算)的区别 —— 本条的 scrollTop **全程不变**, 参考行 rect 瞬偏 ~4px 后缓回; 且**皮肤相关**(atlas/console 有 `.group-head, .group-table { animation: page-in }`, prism 没有, 所以 prism 探针一直干净). 逐帧采样实锤: 换帧瞬间 `.group-table` 计算 transform = `matrix(1,0,0,1,0,4)`, 随后 4→2.4→1.4→0.8→…→0 缓动回位(.22s ease-out 曲线).
- **根因**: 抽屉表格体是**长生命周期元素**(桥 Teleport + 锚保活, anchFill 在整帧换帧 replaceChildren 后把**同一锚元素**插回新 slot 位保持元素身份跨帧存活) ⇒ anchFill 每次换帧把锚摘下再插回 = 元素从文档移除再插入 = **CSS 动画重启** ⇒ page-in(translateY(4px) + 淡入, .22s)在每次点击重渲(数据回路 POST→补拉→换帧 / 行选中 rerender)时整表跳 4px 再缓回.
- **处置**: 两皮肤 views.css 加 `.drawer .group-head, .drawer .group-table, .drawer .h-cell .arrow { animation: none; }` —— 抽屉里表格体不播入场动画(主列表表格随视图真重建才播, 不受影响); 变体 10/11 全中, 对 peers 可排序变体(07/08/09)的 `.h-cell .arrow` 是防御性同款覆盖.
- **守阵**: dt-live-update #9「数据回路点击不跳动: 逐帧采样下行/scrollTop 全程零偏移」(rAF + 4ms 双路采样, 覆盖整个数据回路窗口取全程最大偏移; POST 走真实端点保 waitCmd 链, GET 在 POST 后翻转数据模拟真后端变化).
- **量具教训(本条的元教训, 比根因更值钱)**: **瞬态缺陷必须逐帧采样** —— before/after 比对式量具(#8 那种点前点后各拍一张)必然错过自回位型跳动; 前三轮量具全绿而用户仍报跳动的盲区 = 只测勾选(纯前端态), 没测数据回路(POST→waitCmd→静默补拉→换帧). 报「跳动」类缺陷先问用户「持续多久回位」: 自回位 ⇒ 动画/clamp 类瞬态, 探针间隔必须压到帧级(≤16ms, 本量具用 4ms).
- **家族关系**: 「元素身份保活」与「CSS 动画语义」是**隐式耦合** —— 任何保活/复用元素的机制(锚保活/Teleport/keep-alive/虚拟列表节点复用)都要问一句「摘下再插回会重启什么?」(动画重启/transition 重播/autofocus/媒体播放). 修法一律作用域禁用(动画对保活元素无意义——用户眼里它一直在), 不是删动画定义.
- **复发**: 0
