# 渲染/静态资源/两套 UI 的完整处置与实测证据 — 外迁详情(原 `pitfalls/web-ui/template-render.md` 段落原文)

> 摘要: `pitfalls/web-ui/template-render.md` 的详细处置/实测证据原文外迁(主档为控 cap 原位留指针); 判据与实测证据原样保留。
> 触发: 同主档 `pitfalls/web-ui/template-render.md` 的触发词(完整列表见主档头部)。

> 本文件是**外迁存档**: 主档该段原文一字未改搬来 (仅相对链接整体下移一层 —— 本文件在 `pitfalls/web-ui/attachments/`); 本目录不计 cap, 主档原位留指针。
## 变体渲染是通知驱动的: 状态翻转后必须补一发 _dtNotify, 否则停在旧态到下一拍轮询

- **处置**: 通知一律放 finally、**在 loading 清掉之后**(stale 响应仍不通知不落袋);
  守阵 `test_webui_static_dom_panel.py::test_drawer_tpl_registry_wiring` §4a 断言三 fetcher 内
  `loading = false` 的位置先于 `_dtNotify`。给变体加新消费状态时同问一句: 这个状态翻转
  的每条路径都有通知跟着吗。
- **守阵**: `tests/test_webui_static_dom_panel_drawer.py::test_drawer_tpl_registry_wiring`(§4a 次序断言)。

## sig 跳过重建会把「随时间变化」的派生值冻帧: 时间基准必须计入 sig

- **处置**: 把**时间基准**计入 sig(`nowSec = Math.floor(Date.now()/1000)`, 每秒变 ⇒ 每次通知都重算,
  实际刷新粒度 = 轮询周期)。判据: 变体里凡有"显示值 = f(now)"就必须让 sig 感知 now。
- **守阵**: `tests/test_webui_static_dom_panel_drawer.py::test_drawer_tpl_trackers_per_tracker_reannounce`(断言 sig 含 `nowSec`)。

## Vue <transition> 接 JS 钩子做布局动画: 钩位/几何登记/迟到的 after 钩子三处静默坑

- **处置**: 钩子驱动槽位(父容器)高度插值 + 元素自身收拢(CSS 退场转 absolute 底缘锚定,
  **不得 inset:0 顶锚定** —— 随槽位塌缩把面板顶跑) + closeDrawer 类显式关闭动作先冻结用户
  可见高(同帧零跳变) + seq 代际闸管 rAF 循环 + 豁免 reduced-motion 与窄屏全屏态。实例
  (2026-10-04 抽屉出入过渡): drawer.js 出入过渡块 + `drawer.html` `<transition>` 接线 +
  `shortcuts.js::_kbViewBottom` 优先读 `_drawerAnimTop` 登记值。
- **守阵**: `tests/test_web_shortcuts_drawer.py::test_drawer_transition_dock_anim`(钩位 @enter / 槽位
  插值 / 收场双高同步 / 登记单点消费 / seq 闸 / after 守卫 / 三皮肤 CSS 成对)。

## 挂件类名错配 ⇒ 整页静默废掉

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
- **处置**: **守阵** `tests/test_web_*.py` 的 `_scan_page_class_wiring`(挂在 `test_frontend_static_bundle_health` 第 11 项):
  扫每张 index.html 的 `<main class="...">` 里出现的挂件类名(白名单 `_PAGE_HOOK_CLASSES` = hub-page / ce-page / layout),
  若在任何 CSS(shared/* + 各 *.css)里都找不到对应 `.X {` 规则就红; 已把 `.hub-page` 临时改回 `.hb-page` **红验**过(两套 UI 同时报警)。
  **新增挂件类时同步更新白名单。**

## 静态资源不加 `Cache-Control` 会被浏览器启发式缓存

- **处置**: 现由 `webui/server/static_ui.py` 的 `_static_no_cache` middleware 给所有非 `/api` 响应加 `no-cache`。
- **复发: 1** —— 2026-09-27(界面切换下拉冒烟): 自建桩服务(FastAPI + StaticFiles)挂静态 UI 没抄这条,
  改完 topbar.html 后浏览器仍吐旧分片, 症状与"改了没生效"一模一样, 白查一轮。**为什么没命中**:
  注意力全在改动本身, 没意识到**自建静态服务也必须带 no-cache**(真机的 middleware 不是天然存在的)。

## 自建冒烟桩缺 `/api/config/public` 会被登录遮罩挡死

- **处置**: 桩补 `GET /api/config/public → {"web": {"skip_local_verify": true}}`(再配最小
  `/api/state` 形状); **有 `dev.harness` 就别自建桩** —— no-cache / 免鉴权 / state 形状它都带齐了,
  自建前先 `commands list dev` 查现成 task id。

## 前端表达式错误只有浏览器能发现

- **处置**: 必须做浏览器冒烟, 并**主动触发对应渲染分支**(例: pill 只在限速曲线启用时才渲染)。

## 未闭合的 `<transition>` 会静默吞掉其后所有弹窗

- **处置**: 逐行数 `<transition>` 配对看弹窗所在深度; 修完核对 `.modal-mask` 的父节点**不是** `TRANSITION`。

## CSS 规则漏 `; }`(或选择器头被吞)会让其后规则整段被丢弃

- **处置**: 定位法 —— 把 CSS 文本塞进 `<style>` 比 `sheet.cssRules.length` 与顶层块数,
  二分找第一处"解析数 < 应得数"的行。

## 组件变体用 CSS 变量承载时, 后写的直接属性会让变体静默失效

- **处置**: 全库二选一并统一 —— **主题只覆写变量**, 或**变体直接写属性**。悬停态也需要**独立的文字色变量**。

## 两套 UI(星图 atlas / 棱镜 prism)必须**成对改**

- **处置**: **按选择器在两套 CSS 各 grep 一遍**, 数量对不上就是漏改; 仅改 `shared/app.js`(逻辑层)才天然两套生效。
  改完加**静态计数断言**兜底, 不要只靠肉眼走查。

## "CSS 已入库但模板从未切换"的两不管缺口

- **处置**: 两侧都扫; 重放时判定"跳过"的文件要写明理由并**登记缺口**(见 [../git/sync-pull.md](../../git/sync-pull.md) 双 UI 镜像那条)。

## 删死模板要连带清它独占的 CSS —— 但"死类"判定不能只看带前缀的类名

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

## `cfgFlatten` 的 `group_of` 分组判定不能递归复用

- **处置**: 递归时传 `allowGrouping=false`。
  ⚠ 排查"渲染出来但是空的"最快的是**浏览器控制台 + 模板里临时打一行 `{{ item.items.length }}`**。

## boot.js 的 manifest `"into"` 落点在嵌套 template content 内时, querySelector 够不到

- **处置**: 落点查找必须**逐层递归下钻 `template.content`**(`boot.js` 已实现: querySelector 不中就对
  `root.querySelectorAll("template")` 逐个递归进 content 再找; 找不到 fail-fast 显式占位)。
  给 manifest 换落点后必须真浏览器起盘目检一次, 静态检查发现不了这类落点丢失。

## 变体模板里把 T 标签模板的结果「裸插值」会被全量转义 —— 整段标签当纯文本透出

- **处置**: 条件子块统一写 `` ${cond ? R(T`<...>`) : ""} ``(不是 `` ${cond ? T`<...>` : ""} ``)。判据一句话:
  变体里凡「把 T 标签模板的结果当插值」就必须套 `R()`。修时同批扫全量变体(`drawer_tpl/` + `drawer_pages/`),
  命中两处: `05-trackers-health-groups-low.js`(未启用区虚拟条目备注)、`11-content-treegrid-batch-low.js`
  (筛选无结果的空态)。
- **守阵**: 暂无。可复用的静态扫描判据: 逐个 `${...}` 插值表达式, 内容含 `T` + 反引号却不含 `R(` 即命中。

## 同一个类名既当「容器」又当「行修饰」时, 容器的 max-width 会静默接管行宽

- **处置**: 容器类改名 `.hb-ro-sum`(行 `.hb-ro-sum-line`), 行修饰保持 `.hb-row.hb-ro`。判据一句话:
  **容器类与行修饰类不得同名**, 且改名后裸选择器(`.hb-ro{...}`)必须清零 —— 只改模板不改 CSS 或反之,
  都会让另一半静默失效(摘要容器变裸文本, 或行宽再次被接管)。
- **守阵**: `tests/test_web_traffic_monitor.py::test_frontend_readonly_row_class_not_colliding`(裸
  `.hb-ro` 规则为零 + 容器类成对存在 + 模板跟随改名); 真 DOM 侧在 `e2e/views.spec.mjs` 的 S7 用例内
  (`rowW > blkW - 4` / 值列 `ctW > 400`)。

## 折叠头「整栏可点」时, 里层钮要 aria-hidden —— 但 e2e 的 getByRole 也随之看不见它

- **处置**: e2e 改点**段头本身**(它才是 role=button), 并顺手把 `aria-expanded` 的翻转也断言上 ——
  把可访问性契约变成断言, 而不是只把 locator 换个写法糊过去。别用 `includeHidden: true` 绕:
  那等于把"用户其实点不到这个钮"这件事写进测试。
- **守阵**: `tests/test_webui_static_skins_skin.py::test_frontend_tpl_ctl_bits_single_source`(段头
  role/tabindex/aria-expanded + 内钮 aria-hidden/tabindex=-1 的模板形态); 真手势侧在
  `e2e/views.spec.mjs` 的 B4 用例(`srcHead.click()` + `toHaveAttribute('aria-expanded', ...)`)。
