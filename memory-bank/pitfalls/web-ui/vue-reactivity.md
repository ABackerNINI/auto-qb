# Vue 语义与 SVG

> 摘要: Vue Options API 的三类静默白屏(computed 当函数 / 带参 computed / 三者同名)与 SVG 属性大小写 —— 都**没有运行时提示**。
> 触发: 改前端模板, 改 computed, 改 methods, 改 SVG, 加图标, 白屏, 整块不渲染

### computed 在模板里是**属性**, 不能当函数调用

- **触发**: 在模板或代码里写 `this.xxx()` 而 `xxx` 是 computed(典型: `hasUnit()` / `unitParts().num`)。
- **判别**: 生产版 Vue 抛 `is not a function`, 结果是**整块区域不渲染**(设置页只剩分组标题 / 顶栏整条消失),
  而**控制台常常无醒目提示**。
  ⚠ **真实发生过并被修掉(2026-09-21)**: `ce-field` 的 `setUnitNum` / `setUnitName` 长期写成
  `this.unitParts().unit` / `this.unitParts().num`(而 `unitParts` 是 computed, 返回 `{num, unit}`)⇒
  经典设置页**一改「数值+单位」字段的数字就整页白屏**; 没被发现是因为模板里的 `unitParts.num` 是对的,
  只有真的去改主循环间隔 / 轮转大小这类值才触发。
- **处置**: 改成属性访问 `this.unitParts.unit`。
  **守阵**: `tests/test_web.py::test_frontend_computed_not_invoked_as_function` —— 扫每个片段文件的
  `computed: {` 块成员名, 一旦发现 `this.<名>(` 就红(注释行跳过, 否则守阵会逼人删文档); 已红验。
  ⚠ 带参渲染辅助(如 `unitLabel(u)`)必须放 `methods` —— Vue 3 的 computed getter 被框架以**组件代理**为参数调用,
  收到的 `u` 是 Proxy 而非遍历项, `String(proxy)` 抛 "Cannot convert object to primitive value"。

### 带参数的 computed 是另一条更隐蔽的雷

- **触发**: 在 `computed: {` 块里写 `memberWin(list) {…}`(2026-09-21, issue 26-09-21-0247)。
- **判别**: Vue 仍把它当 **getter** 注册 ⇒ 模板里 `memberPadTop(g.members)` 触发 `this.memberWin` 被当作属性访问 ——
  框架**不会**把 `g.members` 传给 getter(只对 methods 传)⇒ getter 用未定义参数跑完返回一个对象
  `{padTop:0,…}`, 然后 `(list)` 把它当函数调 → `this.memberWin is not a function` ⇒
  **整表白屏**(chips / 状态条 / 表头 / 行 全部消失)。
  坑在编译期不报、lint 阶段单控过、`pytest --passes` 也过 —— **只有能加载页面的脚本里才能复现**。
- **处置**: **带参的"计算"必须一律放 methods**(放 methods Vue 会把模板里的实参原样透传)。
  静态守阵: `tests/test_web.py::test_frontend_member_window_functions_live_in_methods`
  (定位 `methods:` 与 `computed:` 块边界, 断言 `memberWin` / `memberPadTop` / `memberPadBottom` 定义行落在 methods 之内)。
  ⚠ 同坑曾因"没人走那条交互路径"长期潜伏, 真机一走就塌 ⇒ 加新成员窗口函数时**先在两套 UI 都跑一遍展开/收起的冒烟**, 不能只看单测。

### computed / methods / data 三者不能同名 (共命名空间)

- **触发**: 起新名时没查重。
- **判别**: 同名后调用方拿到的是**属性**, 抛错形态同上(整块不渲染)。
- **处置**: 起名后在三处都 grep 一遍。

### 模板里不允许下划线前缀标识符

- **触发**: 写 `{{ _bulkCountText() }}` 这类。
- **判别**: Vue 把 `_` 前缀当**内部保留域** ⇒ 抛 `ReferenceError` 且**整块渲染失败**(控制台只有一行)。
- **处置**: 对外派生值**去掉下划线前缀**。

### SVG 属性大小写敏感

- **触发**: 静态写 `viewBox` / `pathLength`。
- **判别**: 会被模板编译器小写成 `viewbox` ⇒ 浏览器忽略、**内容溢出容器**。
- **处置**: 必须 `v-bind="{ viewBox: ... }"` / `v-bind="{ pathLength: 1000 }"`。

### 内联 SVG 只有 `width:100%; height:auto` 会退化成 150px

- **触发**: 放无固有尺寸的内联 SVG。
- **判别**: 无固有尺寸的替换元素默认 150px。
- **处置**: CSS 显式 `aspect-ratio: <viewBox 宽高比>`。

### 图标一律走 index.html 的 sprite

- **触发**: 加图标。
- **判别**: 约定是 `<use href="#i-*">`, **无外部图标库 / 网络依赖**。
- **处置**: 新增图标只在 sprite 加一个 `<symbol>`; 各 symbol 的 viewBox **可以不同**(按 symbol 自身映射, 使用处不必改)。

### SVG `<use>` 图标想做双色: 外部 CSS 选择器**进不去影子树**

- **触发**: 想按状态改 `<use>` 内部 path 的颜色(2026-09-20 实测)。
- **判别**: 图标是 sprite `<symbol>` + `<use href="#i-*">`, `.ico-today .down { stroke: ... }` 这类选择器
  对 use 内部的 path **无效**; 能继承进去的**只有 CSS 自定义属性**。
- **处置**: 双色只能写成 symbol 内 path 的**内联** `style="stroke: var(--token)"`, 靠 `var()` 在影子树里解析
  (令牌定义在 `:root` / 主题上)。同理, 想按状态改图标局部颜色, **别指望加 class**。
