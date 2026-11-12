# 嵌套浮层单次钳位会被宿主二次收口搬移失效——子面板钳位必须带同款有界复核, e2e 读盒须等收敛

> 摘要: 嵌套浮层单次钳位会被宿主二次收口搬移失效——子面板钳位必须带同款有界复核, e2e 读盒须等收敛
> 触发: 嵌套浮层, 子面板, .ctx-sub, 钳位, 二次收口, _menuFitRefit, _subFitRefit, settle, 锚点搬移, vh-8 契约, clampAxis, e2e 读盒时机, subTop 收敛, currentTarget, 复制哈希被裁
**Refs:** memory-bank/issues/26-11-13-0443-bug-webui-ctx-sub-overflow.html, memory-bank/tasks/26-11-12-webui-kbd-hints.md

## 本篇只回答

右键菜单次级子面板(以及一切「钳位锚点挂在宿主浮层内部元素上的嵌套浮层」)的视口钳位, 为什么单次 `$nextTick` 钳位守不住 `vh-8` 契约、修法与回归断言的读盒时机怎么定。宿主浮层自身的钳位机理(估 + 实测两级)与二次收口循环形态见 `ui_feedback.js::_menuFitRefit` 注释与本篇, 不另拆件。

### 主菜单 `_menuFitRefit` 的 rAF settle 在子面板单次钳位**之后**修正菜单 x/y, 嵌套层不跟随即底缘溢出

- **触发**: 嵌套浮层的钳位锚点挂在宿主浮层内部(子面板锚在父项上、`subTop` 是相对父项的 top 内联值), 且宿主有自己的二次收口(主菜单 `_menuFitRefit` S2 起带 rAF settle)。宿主首钳用的分数像素尺寸未落定(~2px, 键帽 `.aq-kbd` 11px mono 是典型来源), settle 帧按落定尺寸修正 x/y —— 这发生在嵌套层单次钳位**之后**, 锚点(父项)随宿主搬移, 嵌套层的相对位移是按搬移前的锚点算的, 整盒随宿主一起被搬出契约。首行右键 + 悬停「更多操作」必现(菜单贴视口顶, 父项靠视口下部, 双重钳位全部 engage), 四皮肤一致。
- **判别**: ①视觉: 末项贴视口下缘被裁(issue 26-11-13-0443: 末项「复制哈希」行下缘没了); ②数值: 子面板底缘 `getBoundingClientRect().bottom > innerHeight - 8 + 1` 且稳定复现(不是闪帧); ③**instrument 定源**: 页面里包一层 `vm._subFitViewport` 记录钳位时刻的 `want/rect.top/subTop` 与终态 bbox —— 钳位时刻 `want` 精确(892 - offsetHeight)、终态渲染顶却比 `want` 低 ~2px ⇒ 溢出量 == 宿主 settle 的搬移量, 即本坑。别按「首帧量高偏小」假设去查子面板自身尺寸(实测它钳位时刻已是终值 397), 也别怀疑状态栏遮挡(`.ctx-menu` z-index 100 > `.statusbar` 30, 子面板压在状态栏上面画)。
- **处置**: ①嵌套层补同款二次收口: `menu.js::_subFitRefit(anchor, name)` —— `$nextTick` 单钳 + `requestAnimationFrame` 有界复核(1+3 帧收敛, 复核幂等不写回, `this.subMenu !== name` 闸防旧循环把新子面板按旧锚点误钳); ②`openSub` 在事件回调里**同步捕获** `ev.currentTarget` 存进局部再传给量测回调(`hr.js::hrPopEnter` 同款纪律 —— 实测 Vue `$nextTick` 微任务里它恰好还活着, 但那是引擎实现顺序的侥幸, 不许再依赖); ③settle 注册顺序天然正确: 宿主 settle 先注册先跑, 嵌套层复核在同帧后跑, 量到的就是宿主搬完的终态。
- **守阵**: e2e `menus.spec.mjs`「CTX-sub fit 首行场景: 二次收口后子面板整盒仍收进视口」(四边收进断言 + `subTop` 跨两帧 rAF 收敛等待) —— 红绿双验过: 旧代码红(底缘 894 > 893)、修后 20/20 绿; 既有「CTX-sub fit: 子面板整盒收进视口」守的是下半带 arrange 的钳位 engage, 本条守首行 arrange 的收敛终态, 两条互补。
- **复发**: 0

### 浮层位置类 e2e 断言在开层后**立即**读盒, 读到的是复核链收敛前的快照 —— 红验假绿

- **触发**: 给带二次收口的浮层写位置断言, `hover()`/开层后直接 `boundingBox()` —— 宿主 settle 在之后 1~2 帧才搬移, 读到的是搬移前快照, 缺陷被读时机藏住(本坑红验首轮: 旧代码 12/12 全绿, 换 300ms 后读的探针 5/5 红)。
- **判别**: 同一断言「探针带等待 = 红、测试立即读 = 绿」即读时机假象; 或同一场景多次 repeat 偶发红/绿。
- **处置**: 断言前等复核链收敛 —— 用语义信号不用裸 sleep: `expect.poll` 读 `vm.subTop` 跨两帧 rAF 不再变化(收敛), 再读盒断言四边。旧实现 `subTop` 恒不变, 该等待对它即时通过, 判别力全在四边断言上(等待不放过旧代码)。
- **复发**: 0
