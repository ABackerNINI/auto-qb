# 自绘 combobox 收层: 主判据走 @focusout, 且不能同步收(label 转发回焦会闪)

> 摘要: 自绘下拉(combobox)的收层判据若只靠 window click, 「点字段 label(for= 转发激活)」这条路径会关了又开 —— 浏览器对 label 的 mousedown 先 blur 输入框、click 默认动作再把焦点转回, click 关层 + 转发 click 重开落在同一交互里, leave 过渡被打断 = 用户看到的「下拉闪烁再次出现且未失焦」。处置 = 收层主判据改 @focusout, **且必须定时合帧**(同步收层仍会被 ~2ms 后的 focusin 回焦打断); 开层方法先撤销挂起的收层。另: 浮层限高不能只靠 CSS max-height —— 绝对定位溢出会把滚动容器的 scrollHeight 撑大(窗口"变形"), 要在开层时量「锚点→滚动容器可见底沿」净空。
> 触发: 自绘下拉收起, combobox, focusout, blur 收层, label 转发激活, for 属性回焦, 下拉闪烁重现, 点窗口其它位置不收, 下拉撑变形, 浮层限高, add-pop, 转发 click, 合帧守卫, 开层撤销

## 条目

- **触发**: 给"聚焦即展开"的自绘下拉补"点外即收", 或报障「触发下拉后点窗口其它位置, 下拉闪烁再次出现、输入框未失焦」「选项过长把窗口撑变形」(2026-10-03 用户报, 添加种子窗口三下拉: 保存路径/分类/标签)。
- **判别**: ①收层只有 window click(lifecycle.js)一路时, 点字段 label(`for=` 指向下拉输入框)的完整事件链是 mousedown → focusout → **click(label) → window click 收层 → focusin(~2ms 后, label 默认动作转发) → 转发 click 到输入框 → @focus/@click 重开** —— 中间"收层"与"重开"是否被 Vue 批处理取决于浏览器把 label 激活行为派发成同一任务还是相邻任务, 时序依赖 ⇒ **概率性闪烁**, 真机偶发而合成探针难复现; ②几何侧: `.pop-menu { max-height: 330px; overflow-y: auto }` 只保证菜单自身可滚 —— 菜单锚在输入行下方(`.add-pop { top: calc(100% + 4px) }`), 输入行贴近窗口底沿时整条菜单**伸出窗口外**(滚动条跟着出窗), 且绝对定位溢出会把 `.add-dialog-body`(overflow-y:auto)的 scrollHeight 撑大(实测 449→591, 窗口内容"变形")。
- **处置**: ①三输入框挂 `@focusout="addPopBlurClose"`(add_torrent.js 单点), 内部 `setTimeout(40ms)` 收三个浮层; 三个开层方法(openAddCatMenu/openAddTagMenu/openAddPathPop)**先 `_addPopBlurCancel()`** —— 焦点真离开(点空白/别的字段/Tab)下一拍收层, 焦点回来(label 转发/重新点入)则撤销, 菜单全程不闪; window click 降级为兜底不拆。守阵: `test_web.py::test_frontend_add_combo_blur_close_and_fit`(focusout 挂点/合帧守卫/开层撤销/watcher 限高五组断言)。②限高走 `watch` 单点(开层入口四处: 开层方法/输入 @input 直开/键盘 _comboKeydown/候选异步到位, 直挂方法必漏), `_fitAddPop` 在 $nextTick 量 `body.getBoundingClientRect().bottom - row.getBoundingClientRect().bottom` 的净空扣掉面板头, 把可滚内层(`.add-pop-list` 或菜单自身)`style.maxHeight` 限进去(**限前先复位旧值**), 净空下限 120px。验证: Playwright 记录器逐帧抓 transitionrun + 三皮肤 12 项走查(点空白收层/label 点击零过渡重放/40 项菜单不出窗且 body 零新增滚动)。
