# 渲染 / 静态资源 / 两套 UI

> 摘要: 模板与 CSS 的静默失效(挂件类名错配、规则被吞、变体被覆盖、注入落点找不到)与"两套 UI 必须成对改"的纪律。
> 触发: 改模板, 改 CSS, 加挂件类, 改主题, 两套 UI, 白屏, 静默失效, 缓存, 过渡, 组件变体, 删死代码, 死类判定, 混合选择器, 动态类名, 删模板连带清 CSS, boot.js, 注入落点, manifest into, 停靠面板

### 挂件类名错配 ⇒ 整页静默废掉

- **触发**: 在 index.html 的 `<main class="…">` 上写挂件类名(2026-09-21 实测, 用户报「输入框缺发光 + 排版竖着」)。
- **判别**: CSS 里写 `.hb-page`、HTML 上是 `class="ce-page hub-page"` ⇒ `.hb-page` 选择器**永远不命中任何元素** ⇒
  其上定义的 `--tone` / `--glow` / `--glow-soft` / `--hb-font-mono` 等令牌**从未定义** ⇒
  所有 `var(--tone)` 派生值替换时判为无效 ⇒ **描边回退、发光整条消失、等宽字体也不生效**
  (剩下字体 fallback 救命, 所以看着还像那么回事)。
  同一波里 `.hb-wrap` 漏写 `width: 100%` 也踩了一脚: 它是 `.ce-page`(flex column)下的 flex item,
  用了 `margin: 0 auto` 之后 `align-self: stretch` 就不再拉伸(规范里 **auto 外边距优先**)⇒
  宽度退化成 fit-content ⇒ 实测只 **484px** ⇒ 卡片网格 `auto-fill minmax(272px)` 只排得下 1 列,
  **表现为「竖着排」**。
  **关键**: 这类错误**没有运行时报错**, 靠真浏览器量 computedStyle / boundingBox 才看得出来, 静态检查天然看不见 ⇒ **必须机检**。
- **处置**: **守阵** `tests/test_web.py` 的 `_scan_page_class_wiring`(挂在 `test_frontend_static_bundle_health` 第 11 项):
  扫每张 index.html 的 `<main class="...">` 里出现的挂件类名(白名单 `_PAGE_HOOK_CLASSES` = hub-page / ce-page / layout),
  若在任何 CSS(shared/* + 各 *.css)里都找不到对应 `.X {` 规则就红; 已把 `.hub-page` 临时改回 `.hb-page` **红验**过(两套 UI 同时报警)。
  **新增挂件类时同步更新白名单。**

### 静态资源不加 `Cache-Control` 会被浏览器启发式缓存

- **触发**: 升级前端后"界面改了但没变"。
- **判别**: `StaticFiles` **只给 ETag** ⇒ 浏览器启发式缓存旧前端, 并**误导排查**。
- **处置**: 现由 `webui/server/static_ui.py` 的 `_static_no_cache` middleware 给所有非 `/api` 响应加 `no-cache`。
- **复发: 1** —— 2026-09-27(界面切换下拉冒烟): 自建桩服务(FastAPI + StaticFiles)挂静态 UI 没抄这条,
  改完 topbar.html 后浏览器仍吐旧分片, 症状与"改了没生效"一模一样, 白查一轮。**为什么没命中**:
  注意力全在改动本身, 没意识到**自建静态服务也必须带 no-cache**(真机的 middleware 不是天然存在的)。

### 自建冒烟桩缺 `/api/config/public` 会被登录遮罩挡死

- **触发**: 自建桩挂静态 UI 做浏览器冒烟, 页面只渲染「请输入 WEB 访问密钥」, 主界面 DOM 完全不渲染。
- **判别**: boot 先读 `/api/config/public`, 响应里 `web.skip_local_verify` 非 true 就走密钥表单分支 ——
  纯静态桩不带这个端点 ⇒ 遮罩永不放行(`authRequired` 初值 true, 唯一放行点在验证成功/免鉴权标志)。
- **处置**: 桩补 `GET /api/config/public → {"web": {"skip_local_verify": true}}`(再配最小
  `/api/state` 形状); **有 `dev.harness` 就别自建桩** —— no-cache / 免鉴权 / state 形状它都带齐了,
  自建前先 `commands list dev` 查现成 task id。

### 前端表达式错误只有浏览器能发现

- **触发**: 改任何前端渲染逻辑。
- **判别**: 后端字段 / 接口全对、pytest 全绿而**页面崩**是常态。
- **处置**: 必须做浏览器冒烟, 并**主动触发对应渲染分支**(例: pill 只在限速曲线启用时才渲染)。

### 未闭合的 `<transition>` 会静默吞掉其后所有弹窗

- **触发**: 加弹窗 / 改过渡。
- **判别**: `<Transition>` 只渲染**第一个**子节点, 其余全部被丢弃 —— 点击毫无反应、**控制台零报错**、
  DOM 里**连元素都没有**。
- **处置**: 逐行数 `<transition>` 配对看弹窗所在深度; 修完核对 `.modal-mask` 的父节点**不是** `TRANSITION`。

### CSS 规则漏 `; }`(或选择器头被吞)会让其后规则整段被丢弃

- **触发**: CSS 改了没生效。
- **判别**: 全文件花括号可能**仍配平** ⇒ 数括号查不出来。
- **处置**: 定位法 —— 把 CSS 文本塞进 `<style>` 比 `sheet.cssRules.length` 与顶层块数,
  二分找第一处"解析数 < 应得数"的行。

### 组件变体用 CSS 变量承载时, 后写的直接属性会让变体静默失效

- **触发**: 主题里同时写变量与属性。
- **判别**: `.btn{background:var(--btn-bg)}` + 主题里又写 `.btn{background:#000}` ⇒ 变量声明变**死代码**。
- **处置**: 全库二选一并统一 —— **主题只覆写变量**, 或**变体直接写属性**。悬停态也需要**独立的文字色变量**。

### 两套 UI(星图 atlas / 棱镜 prism)必须**成对改**

- **触发**: 改状态色 / 令牌族 / 修饰符类。
- **判别**: 同一个状态开关(`v-if="xxxOpen"`)在模板里出现**两次以上**基本可断定是遗漏的旧实现(实测"点一次开两窗")。
- **处置**: **按选择器在两套 CSS 各 grep 一遍**, 数量对不上就是漏改; 仅改 `shared/app.js`(逻辑层)才天然两套生效。
  改完加**静态计数断言**兜底, 不要只靠肉眼走查。

### "CSS 已入库但模板从未切换"的两不管缺口

- **触发**: 迁移 / 重放模板提交时。
- **判别**: 静态 class 覆盖检查必须**双向**做 —— "模板用到但 CSS 未定义"**与**"CSS 定义了但模板从不使用"。
- **处置**: 两侧都扫; 重放时判定"跳过"的文件要写明理由并**登记缺口**(见 [../git/sync-pull.md](../git/sync-pull.md) 双 UI 镜像那条)。

### 删死模板要连带清它独占的 CSS —— 但"死类"判定不能只看带前缀的类名

- **触发**: 删掉一个已不可达的模板块(2026-09-25 实测: 经典设置页移除后 `tpl-ce-field` 仍留在两套
  index.html 里, 唯一引用是**自身模板内**的递归 ⇒ 永远不渲染, 但它独占的 40 个 `.ce-*` 类还占着
  177 条 CSS 规则)。
- **判别**: 判"某个类是否已死"必须**全语料 + 双向**: CSS 里定义了, 且 html 的 `class=` / `:class=`
  属性与 js 字符串字面量里**零引用**(扫描前先剥注释, 注释里的类名会把它误判成活类)。
  ⚠ **两个坑**:
  ①**动态类**永远不出现在语料里(`'ceg-' + n`、`is-pattern`)⇒ 要靠"CSS 定义集 − 语料引用集"的差值捞;
  ②**混合选择器**(`.pop-count, .ce-num, .hist-axis text, .topbar .ver`)里**没前缀的活类**最容易被漏算 ——
  只挑带前缀的类名参与判定, 会把这条整规则误判成"纯死"**整条删掉**, 连带干掉活分支。
  **判定必须拿选择器里的全部类名参与**。
- **处置**: ①删模板 → ②算死类集 → ③CSS **逐条规则**判(所有列表项都死才整条删; 有活项则**只摘死分支**)
  → ④**反向校验**: "被引用但 CSS 无定义"的集合**不得扩大**(与 HEAD 逐类对比, 这是"删多了"的唯一机械兜底)
  → ⑤ 真浏览器复量 + 冒烟。静态守卫能兜住括号配平与挂件类名, **兜不住"删多了"**。
  同批还应顺手清掉模板独占的**自定义属性**(本例 `--ce-label-w`/`--ce-ctl-gap`/`--ce-row-pad-x`),
  但只被活规则引用的要留(本例 `--ce-input-max` 仍被 `.ce-note` 用)。

### `cfgFlatten` 的 `group_of` 分组判定不能递归复用

- **触发**: 改设置页配置扁平化 / 分组。
- **判别**: 子卡内字段**已归属父字段**, 再参与分组会把它们收进 children 而 **roots 为空** ⇒
  子卡渲染成**空壳且不报错**。
- **处置**: 递归时传 `allowGrouping=false`。
  ⚠ 排查"渲染出来但是空的"最快的是**浏览器控制台 + 模板里临时打一行 `{{ item.items.length }}`**。

### boot.js 的 manifest `"into"` 落点在嵌套 template content 内时, querySelector 够不到

- **触发**: 给 tpl-manifest 条目换注入落点(2026-10-03 抽屉重设计: drawer 从 `"into": "app"` 改指种子视图模板内部的
  `.drawer-dock`) —— 落点容器写在某个 `<template>` 的 content 里, 外层模板本身又是 boot.js 先注入的。
- **判别**: 顶层 `root.querySelector(sel)` 查不到报"落点找不到"是显性的; 更隐蔽的是
  `querySelectorAll("template")` **不会下钻** `template.content` 片段, 而模板存在浏览器解析出的**嵌套**
  (template 套 template), 只展开一层照样漏 —— 症状是"落点偶发找不到", 取决于哪个嵌套分支被走到。
- **处置**: 落点查找必须**逐层递归下钻 `template.content`**(`boot.js` 已实现: querySelector 不中就对
  `root.querySelectorAll("template")` 逐个递归进 content 再找; 找不到 fail-fast 显式占位)。
  给 manifest 换落点后必须真浏览器起盘目检一次, 静态检查发现不了这类落点丢失。
