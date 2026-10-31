# Vue 组件内字符串 ref 注册在子组件实例: 根方法读根 `$refs` 恒拿不到

> 摘要: 把带 DOM ref 的模板块从根模板抽成子组件时(combobox 五处收敛 issue 26-10-20-2230), 模板里的字符串 `ref="x"` 会注册到**子组件实例**的 `$refs`, 而量测/滚动方法是**根方法**、读的是根实例 `$refs` —— 两边对不上, 且 Vue 不报错: 限高(_fitAddPop)与滚动跟随(_hiScroll)静默失效, 控制台零线索。修法 = 经**方法函数 ref** 把元素代写到根 `$refs`(`:ref="comboBindMenu"` → `this.$root.$refs[name] = el`), 跨组件边界且全生命周期(开/关/重渲染)可靠; `:ref="null/undefined"` 安全(不注册), `:ref=""` 会注册空字符串键。另: 组件方法名全局唯一(_scan_mixin_wiring 扫 methods 段跨文件重名), comboOn*/comboBind* 前缀。
> 等级: L0
> 触发: 组件 ref, $refs, 字符串 ref, 方法函数 ref, 跨组件 ref, 根实例 $refs, 拆组件收敛, combobox 组件, aq-combo-input, _fitAddPop, _hiScroll, 限高失效, 滚动跟随失效, ref 归属, 子组件实例

### 抽组件时模板里的 `ref` 归属会悄悄换实例: 根方法量不到 DOM, 不报错只是静默失效

- **触发**: 把原本写在根模板里的「输入行 + 自绘面板」骨架抽成子组件(本项目即 combobox 五处收敛: dialogs-mgr.html 三处 / move-dialog.html / popovers.html → `aq-combo-input`, issue 26-10-20-2230)。原骨架里 `ref="addCatList"` / `ref="movePathList"` 等是给**根方法** `_fitAddPop(refName)` / `_hiScroll(refName)` 量 DOM 用的(`this.$refs[refName]`)。
- **判别**: 收敛后下拉的限高与键盘滚动跟随**静默失效** —— 症状是「选项过多时窗口被撑变形」(限高没量) / 「上下键选中项不滚进可视区」(滚动跟随没量), 但没有任何报错: `this.$refs[name]` 是 `undefined`, `if (!inner) return` 早退, 控制台干净。用 Chromium 探针实测 Vue 3.5.13: 子组件模板内字符串 ref 注册在**子组件实例**的 `$refs`(父/根都读不到); `:ref="null/undefined"` → `vnode.ref=null` 安全不注册; `:ref=""` 会注册一个空字符串键; **方法函数 ref**(`:ref="fn"`, fn 内写 `this.$root.$refs[name] = el`)可跨越组件边界, 开层/关层/重渲染全周期验证正确。
- **处置**: 组件模板一律用方法函数 ref 代写到根 `$refs`(add_torrent.js 的 `comboBindMenu/List/Input`, 名字为空 = 该处不需要 ref); 字符串 ref 只在「父组件模板直接写子组件标签」时归父实例 —— 收敛场景恰好相反(根模板调组件、组件内部持 ref), 想当然必踩。改动后须跑守阵 `test_frontend_move_dialog_combobox_wiring`(钉 menu-ref 调用点) + e2e 真浏览器验限高/滚动行为。
- **守阵**: `tests/test_webui_static_dom_panel.py::test_frontend_move_dialog_combobox_wiring`(menu-ref 接线) / `test_frontend_add_combo_blur_close_and_fit`(组件模板 @focusout 与调用点 @blur 成对) / `test_frontend_dialog_combo_hover_takeover`(comboOnHover 按 comboKey 转发 $root)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
