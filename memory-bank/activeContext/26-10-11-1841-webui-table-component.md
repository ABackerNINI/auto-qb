# WEBUI 表格公共组件 · 表壳与明细单元格渲染器落地(P1/P2)

> 摘要: 专题 `webui-table-component` 续作。计划 [26-10-11-1722](../plans/26-10-11-1722-plan-webui-table-component.html) 的 **P1/P2 已落地**: 表头块(**5 份**逐字近似)收敛为**单份表壳组件** `<aq-table>`, 明细成员单元格(**2 份**)收敛为**单份行模型渲染器** `<aq-member-cells>`(辅种页/追剧页共用); 两个组件只贡献**模板**, 行为一律经 `$root` 回调根实例。验收: 真浏览器 A/B **DOM 逐字节等价**(17 项探针 × 2 皮肤, 差异 0) + e2e 与基线逐位一致 + 全量守阵绿。P0(表注册表)结论已在档案里, 本切片不复述。P3–P6 待续。
> 最后活动: 2026-10-11 18:41

## 正在进行

- P1/P2 已落地。P3–P6 待起: P3 = 单元格渲染器按行模型归拢(127 条 `v-if` 分支); P4 = 列选择器 / 横滚同步 / 排序键三处重复收敛; P5 = 设置页 HR 表接入(只借壳); P6 = 详情面板只留前向契约。
- 本会话实测数字见 `commands run kb.baseline`。

## 关键结论

- **组件只贡献模板, 行为一律经 `$root` 回调根实例**。本应用是「单根组件 + 全局 mixin」架构: 全局 mixin 让**子组件也有方法域**, 但**根数据**(`sortKey`/`colDrag`/`viewMode`/`timeFmt`/filters…)只在根实例上 —— 子组件里写 `this.xxx` 会读到 undefined(排序键恒空 / 筛选高亮失灵), **静默**。故组件模板一律 `$root.xxx(...)`, 组件自身不复制任何方法实现(复制会触发 mixin 重名守阵)。这条需要把 `$root` 加进「模板禁 `_`/`$` 前缀标识符」守阵的**内建白名单** —— 与 `$event` 同口径: Vue 内建(实例上真实存在、模板可解析)≠ 用户成员(被排除在组件代理外)。
- **表头组件化后 `$refs[headRef]` 拿到的是组件实例, 不是元素**。`_headEl(page)` 统一 unwrap(`el.$el || el`); 三个 `sync*HeadScroll` 与 `_winContainer("member")` 一律改走 `_headEl` —— 直接读 `$refs` 再 `head.style.transform = …` 会 TypeError(横滚同步整条挂), 而 `head.parentElement` 只会静默得 null(成员行窗口化退化成全量渲染, 界面看不出)。
- **"零回归"可以按 A/B 逐字节证, 目测不算**。把 11 个改动文件还原到 HEAD + 删掉新片段, 跑同一 stub 探针(表头/明细头 `outerHTML` + 子节点骨架**含注释与文本节点** + grid 内联样式 + `col-align-css` + `.content` 子元素序), 与新构建逐项比对 —— 差异 0 才是判据。探针是临时件, 不进仓库(方法可复用: 同一 spec 两次跑, 换 tag 落盘后 diff)。
- **收敛会连带改守阵的"计数锚", 必须同轮补覆盖而不是放宽**。明细单元格从 2 份副本并为 1 份渲染器后, 任何按**字面调用**计数的守阵都会变数(HR 安全档位: `hrDurClass(m)`/`hrSrcHalf(m)`/`hrPopEnter` 等触发面 3 → 2; 站点格守阵从"扫两页"改为"扫渲染器")。计数改了就必须把「两页共用同一渲染器」的关系钉到别处(`_scan_column_cells_paired` 钉两个调用点都走 `<aq-member-cells>`, `test_frontend_table_shell_single_point` 钉表壳调用点与把手齐备), 否则等于悄悄放宽。
- **表壳单点由新守阵钉住**: `test_frontend_table_shell_single_point` —— ①两个组件都 `app.component` 注册; ②`tpl/xtpl.html` 里 `#tpl-aq-table` 恰一份且四件交互把手(`.h-cell`/`.h-label`/`.arrow`/`.resizer`/`.col-drop-line`)齐备(丢一件 = "拖了没反应/右键没菜单", 无报错); ③`groups.html`/`shows.html` 各 2 个 `<aq-table>` 调用点、`.h-cell` 内联零残留。**种子页(torrents.html)表头本轮未迁移**(计划 P2 停手点: 只做 group/show/detail), 是 `.h-cell` 残留的显式例外 —— 迁移时把例外删掉。
- **组件模板放 `tpl/xtpl.html` 的 x-template**(与 `hub-field` 同范式), 该分片由清单注入 **body**(在 `#app` 之外)⇒ 不被当作根模板编译、不多包 DOM 层。`prism/index.html` 贴着 **210 行硬顶**, 往清单加一行必须先删一行(本轮删了 `#app` 与清单之间那行空行)。
- **四项交互已真浏览器取证**(e2e 现有轨道只覆盖拖宽 + 表头盒子模型, 排序 / 表头右键 / 拖拽重排无覆盖): 排序三态 + 箭头 + 行序真重排 / 表头右键菜单 / 菜单隐藏列 / 拖拽重排(组件渲染出 `.col-drop-line`、表头可见列序 == 可见列模型序)/ 明细头 scope=detail / 追剧头独立排序键 + 拖宽固化 —— 两皮肤全绿。探针是临时件; 其两个**假红**陷阱(拖拽收尾的 swallow 吃掉紧随的一次 click; 浮层离场动画期间仍 `elementFromPoint` 命中并拦截点击)已记 [pitfalls/testing/smoke.md](../pitfalls/testing/smoke.md)。
