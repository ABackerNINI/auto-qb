# 拆分与统一后的前端守阵口径

> 摘要: 模板/样式/内核三层拆分 + 单一语义模板收敛(2026-09-27)后, 找前端内容与加守阵的固定口径 —— 一律读「聚合」, 模板级 UI 差异只走「差异口」, data/生命周期不许进 app.mixin。
> 触发: 改守阵, 找模板内容, 加断言, 两套 UI 差异, 拆分, 聚合读法, 差异口, ui-diff, 根选项, app.mixin, hub-field, boot.js, 冒烟等价, 搬迁方法体, 拆文件守阵假红, v-if 链跨分片, 新分区, settings.html 上限, 默认值梯, cfgDefaultScalar, cfgDefaultForFields, cfgDefaultForPlugin, 新增条目初值

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md, memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md

### 找模板/CSS/JS 内容: 一律读「聚合」, 别单读拆分前的文件

- **触发**: 给前端加守阵 / 找某段模板或样式在哪 / 断言某成员存在。
- **判别**: 拆分后单读 `index.html` / `atlas/style.css` / `app.js` 会**假绿或假红** —— 模板在 `shared/tpl/*.html`、atlas 样式在 `css/{components,views,dialogs}.css`、根组件成员在 `state.js`/`lifecycle.js`、方法域在 `auth.js`/`polling.js`/`view.js`。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 模板级 UI 差异只走「差异口」, 私拷副本即红

- **触发**: 两套 UI 某块要长得/行为不一样时(如棱镜的主题切换器)。
- **判别**: 绕开机制复制一份分片 = 双模板副本回潮 —— 静默恢复「成对改」人肉纪律。守阵三查: 残留 `<ui>/tpl/` 目录、双 shell 清单漂移、`shared/tpl` 孤儿分片。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 三份 shell 内联段(sprite / #app+login) parity 守阵

- **触发**: 改任一 `src/auto_qb/webui/static/<ui>/index.html` 的图标 sprite 段(加/改图标)或登录遮罩段(`#app` + `login-mask`)。
- **判别**: 三 shell 除 head 资源清单外逐字同约 87.5%(manifest 74 行 / sprite 80 行 / `#app`+login 31 行), 但是**三份物理拷贝** —— 漏改一份的表现是"某皮肤下该图标空白且无任何报错"(登录遮罩则是首屏第一眼、在任何 JS 之前渲染的块)。合并唯一路径是后端渲染时注入, 会让 `index.html` 失去"可直接静态打开"的能力(测试亦直接读盘), 属**能力回退** —— 定案是"不合并, 补齐守阵"(R23-C, 台账 `tasks/26-10-20-frontend-dup-code-audit.md`)。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### schema→默认值梯单点(cfgDefaultScalar / cfgDefaultForFields / cfgDefaultForPlugin)

- **触发**: 新增/改一种字段 `kind`(或插件 `spec_kind`)的默认值规则; 动「新增条目 / 打开可选段」时填进去的初始值。
- **判别**: 这条阶梯曾有三份实现且互相嵌套(可选段 `cfgDefaultForField` / 插件 spec / 插件 section)—— 加一种 kind 要三处同改, 漏一处新条目就过不了后端校验或写出非法空值(默认值直接影响保存合法性)。合并时**不能**顺手统一口径: 三处各留了刻意的分歧 —— 插件 bool 初值 `"true"`(新动作默认开) vs 字段 bool `"false"`; object spec 只填必填而它的 object 子段按**全字段**口径; 可选段非 object 字段历史口径是 `[]`; 未知 `spec_kind` 沿用子表单。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 列表外壳两件套单点(`aq-row-pad` / `aq-empty`)—— 几何契约与三皮肤 CSS 契约都在结构里

- **触发**: 给列表加行窗口化占位(`row-pad`)、加/改空态(`.empty`)、或者新开一个列表视图(groups / torrents / shows 之外)。
- **判别**: 这两块此前各抄多遍且**互相独立地漂** —— ①`row-pad` 是 P1-2 **行窗口化契约**: 上下占位撑住滚动容器总高, 滚到底与滚动条长度才与全量渲染一致; 四处手写意味着改一处 `aria-hidden` 或 px 写法另三处不同步**零报错**, 症状是两个视图的滚动几何悄悄分叉。②`.empty` 的结构不是"随便一个 div": 三皮肤 `components.css` 直接按 `.empty`(flex 纵列居中)与 `.empty .ico` 选择 —— 包一层 wrapper 或改类名就**整条空态样式静默失效**(页面不报错, 只是空态变成左上角裸文字)。③空态图标的语义分工(加载中 / 出错 / 空)长期无文档, 新增的人只能临摹邻近处 ⇒ 设置页 HR 三张表的空态连 `<svg>` 都没写。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### data/computed/watch/生命周期不许进 app.mixin —— 根选项专属

- **触发**: 给根组件加状态字段 / 侦听器 / 生命周期钩子时。
- **判别**: `app.mixin` 是**全局** mixin, 波及该 app 下**所有**组件实例(含 hub-field)—— mounted 双份 = 监听器翻倍 + fetch 双发, watch 双份 = 回调双跑; 全部静默, pytest 不可见。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 片段文件里定义「非 mixin 的 window.* 单例」会被接线守阵判漏注入

- **触发**: 在 shared/*.js 片段里定义一个**不是 Vue mixin** 的全局单例(如快捷键存储适配器
  `window.AQB_KEYS`)供同文件或跨文件直接消费。
- **判别**: `_scan_mixin_wiring` 只认 `^window\.(\w+) = \{` 字面量形态并要求它被
  app.mixin/app.component/`...window.X`/Object.assign 基座四种形态接线 —— 适配器这类「被 JS
  直接调用」的单例不在名单里, pytest 直接红「定义了 window.X 但 app.js 没有 app.mixin(window.X)
  (片段漏注入)」。它不是守阵误报要放宽, 而是书写形态约定。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 新增 shared/ 片段文件的接线清单(三份清单 + app.mixin + prism 的 shell 218 行硬顶)

- **触发**: 往 `shared/` 下**新增一个 `.js` 片段文件**(不是改现有文件), 或新增一个 `shared/tpl/*.html` **模板分片**。
- **判别**: 漏一处都**静默或半静默** —— ①`.js` 漏进 `tpl-manifest.scripts` / `.html` 漏进 `parts` → 文件根本不加载, 页面不报错、那块功能整块不存在(盘上有、清单没挂的 `tpl/*.html` 还会被 `test_frontend_template_split_wiring` 的**孤儿分片**项单独判红); ②三份 shell 的清单必须**逐项一致**(清单等价断言比对的是**解析后的 manifest**, 不是 shell 文本); ③`.js` 里写了 `^window.X = {` 却没接 `app.mixin` → `_scan_mixin_wiring` 判「定义了 window.X 但 app.js 没有 app.mixin」(**模板分片无此步** —— 它只贡献 markup)。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 再拆前端大文件: 等价性验证 = 切割自验 + 真 API stub 冒烟 DOM 比对

- **触发**: 拆任何模板/样式/JS 大文件时(W1/W2a/W2b 已各有一套, 复用方法)。
- **判别**: 静态守阵抓不住**载入期**错误 —— 实测 W2b 切分脚本把原 `const app = createApp({` 残留造成双重声明, pytest 全绿而页面不挂载, 是 stub 冒烟的 `data-drv-mounted` 现形的。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 搬迁方法体(拆文件)时: 按文件名定位的静态守阵要同轮改「读取面」, 不是放宽断言

- **触发**: 把一段实现从 `<old>.js` **搬到**新文件(不是新增片段)时(计划 26-10-11-2106 W1: `drawer.js` → `drawer_store.js` 的数据/行为层)。
- **判别**: 一批守阵是**按文件名读取**来定位方法体的(`_read("<file>.js")` / `open(os.path.join(shared, "<file>.js"))` 后对文本跑正则), **不读聚合** —— 方法体一搬走, 它们整批判「找不到方法体」。这与上一条「加**新**守阵一律读聚合」不冲突: 老守阵的 `_read(<文件>)` 本身就是它钉的契约(方法住在哪个文件), 搬迁即改了契约。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 组件片段只贡献模板: 行为与根数据一律经 `$root` 回调根实例

- **触发**: 往 `shared/` 加一个**只渲染模板**的 Vue 组件(表壳 `<aq-table>` / 明细单元格渲染器
  `<aq-member-cells>`, 计划 26-10-11-1722 P1/P2), 组件里要调格式化 / 筛选 / HR 口径等方法。
- **判别**: 全局 mixin 让**子组件也有方法域**, 于是 `this.fmtSizeOrDash(...)` 看着能用 —— 但
  **根数据**(`sortKey`/`colDrag`/`viewMode`/`timeFmt`/filters…)只挂在**根实例**上, 子组件里读到
  的是 undefined: 轻则排序键恒空 / 筛选高亮失灵, 重则 `this.timeFmt[key]` 直接 TypeError —— 两种
  都是「页面照常渲染」的形态, 静态守阵看不出, 只能靠真浏览器。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

- 原生 `<table>` 里上组件必须借 `<tr is="vue:…">` 占位; v-for 会插零长文本锚点(P5): 详见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 收敛模板会连带改掉按「字面调用」计数的守阵 —— 同轮补覆盖, 不是放宽

- **触发**: 把 N 份重复模板并成一份(或把内联片段搬进组件)之后跑全量测试。
- **判别**: 一批守阵是靠**在聚合模板里数某个字面调用出现几次**来钉接线的(HR 安全档位: 做种时长
  列的 `hrDurClass(m)`/`hrSrcHalf(m)`/`hrPopEnter($event, m)` 各 3 处触发面; 站点格守阵扫两页
  模板)。副本一合并, 计数必然变(3 → 2), 页面本身没坏 —— 这是**收敛的必然**, 不是漏改。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)

### 设置页分区模板: `v-if/v-else-if` 链**跨分片**延续 —— 新分区只能作链尾 `v-else-if`, 且 settings.html 逼近 400 行上限

- **触发**: 给设置页加一个新分区(新 schema Group 的二级页)。
- **判别**: 二级页分支是一条 `v-if`(trackers) / `v-else-if`(rules) / … / `v-else` 的**连续链**, 起点在
  `tpl/settings.html`、中途在 `tpl/settings-detail.html`(链的 `v-else-if speed/keys` 与收尾 `v-else` 都在后者;
  后者还自带 `</main>`)。分片按清单顺序拼进 `#app`, 于是**链跨文件延续**:
  - 想在**链中**插分支(settings.html 末尾与 settings-detail.html 之间插一个 `v-else-if`)会**打断链** ——
    其后所有 `v-else-if` 立刻失配(整块静默不渲染, pytest 全绿);
  - 想插在**链尾之后**又落在 `</main>` 之外(`hub.view` 是持久化值, 面板会在非设置页也渲染)。
- **处置**: 详细步骤与实测证据见 [attachments/frontend-split-details.md](attachments/frontend-split-details.md)
