# 拆分与统一后的前端守阵口径

> 摘要: 模板/样式/内核三层拆分 + 单一语义模板收敛(2026-09-27)后, 找前端内容与加守阵的固定口径 —— 一律读「聚合」, 模板级 UI 差异只走「差异口」, data/生命周期不许进 app.mixin。
> 触发: 改守阵, 找模板内容, 加断言, 两套 UI 差异, 拆分, 聚合读法, 差异口, ui-diff, 根选项, app.mixin, hub-field, boot.js, 冒烟等价

### 找模板/CSS/JS 内容: 一律读「聚合」, 别单读拆分前的文件

- **触发**: 给前端加守阵 / 找某段模板或样式在哪 / 断言某成员存在。
- **判别**: 拆分后单读 `index.html` / `atlas/style.css` / `app.js` 会**假绿或假红** —— 模板在 `shared/tpl/*.html`、atlas 样式在 `css/{components,views,dialogs}.css`、根组件成员在 `state.js`/`lifecycle.js`、方法域在 `auth.js`/`polling.js`/`view.js`。
- **处置**: 统一走聚合助手 —— 模板 `_ui_aggregate(ui)`(shell 内联段 + 分片按 tpl-manifest 清单序)、CSS `_ui_css_aggregate(ui)`(按 shell link 序, 级联序=link 序)、JS `_app_bundle_text()`(清单序整包); 清单本身就是单一来源(tpl-manifest / head link / manifest scripts), 别在守阵里另抄一份顺序。

### 模板级 UI 差异只走「差异口」, 私拷副本即红

- **触发**: 两套 UI 某块要长得/行为不一样时(如棱镜的主题切换器)。
- **判别**: 绕开机制复制一份分片 = 双模板副本回潮 —— 静默恢复「成对改」人肉纪律。守阵三查: 残留 `<ui>/tpl/` 目录、双 shell 清单漂移、`shared/tpl` 孤儿分片。
- **处置**: `<template v-if="ui === 'atlas'|'prism'">` 条件块 + 块前 `ui-diff:` 注释说明原因; `_scan_ui_diff_registry` 收集全部条件块作为「活差异清单」(取值只认两 UI, 注册表为空也红 —— 机制必须保持存活)。参数化小差异(如界面切换下拉的选项表)优先走 computed(`uiCurrent`/`uiOptions`, 数据单点 `UI_HOME`)而非条件块。
- **守阵**: `test_frontend_template_split_wiring`。

### data/computed/watch/生命周期不许进 app.mixin —— 根选项专属

- **触发**: 给根组件加状态字段 / 侦听器 / 生命周期钩子时。
- **判别**: `app.mixin` 是**全局** mixin, 波及该 app 下**所有**组件实例(含 hub-field)—— mounted 双份 = 监听器翻倍 + fetch 双发, watch 双份 = 回调双跑; 全部静默, pytest 不可见。
- **处置**: 根组件的 data/computed/watch 在 `state.js`、生命周期在 `lifecycle.js`, 经 app.js 的 `...window.X` **展开进 createApp 根选项**(只命中根); 方法域(auth/polling/view 与业务片段)才走全局 mixin。接线由 `_scan_mixin_wiring` 形态④钉住(只认 app.js 内 `...window.X` 展开, 不放宽)。
- **守阵**: `test_frontend_mixin_wiring`(挂 test_frontend_static_bundle_health)。

### 片段文件里定义「非 mixin 的 window.* 单例」会被接线守阵判漏注入

- **触发**: 在 shared/*.js 片段里定义一个**不是 Vue mixin** 的全局单例(如快捷键存储适配器
  `window.AQB_KEYS`)供同文件或跨文件直接消费。
- **判别**: `_scan_mixin_wiring` 只认 `^window\.(\w+) = \{` 字面量形态并要求它被
  app.mixin/app.component/`...window.X`/Object.assign 基座四种形态接线 —— 适配器这类「被 JS
  直接调用」的单例不在名单里, pytest 直接红「定义了 window.X 但 app.js 没有 app.mixin(window.X)
  (片段漏注入)」。它不是守阵误报要放宽, 而是书写形态约定。
- **处置**: 写成 `const X_ADAPTER = {...}; window.X = X_ADAPTER;`(赋值右侧不是 `{` 字面量,
  守阵不命中), 并在注释里写明「这是被直接消费的单例, 不走 app.mixin」。键盘快捷键 W1 实测
  (shortcuts.js AQB_KEYS, 2026-09-30); W6 后端存储接入时同形态。
- **复发**: 0

### 新增 shared/ 片段文件的接线清单(三份清单 + app.mixin + prism 的 210 行硬顶)

- **触发**: 往 `shared/` 下**新增一个 `.js` 片段文件**(不是改现有文件)。
- **判别**: 四处漏一处都**静默或半静默** —— ①漏进 `tpl-manifest.scripts` → 文件根本不加载, 页面不报错、那块功能整块不存在; ②三份 shell 的 `scripts` 清单必须**逐项一致**(清单等价断言比对的是**解析后的 manifest**, 不是 shell 文本); ③文件里写了 `^window.X = {` 却没接 `app.mixin` → `_scan_mixin_wiring` 判「定义了 window.X 但 app.js 没有 app.mixin」(与下一条同族, 但这条是**新文件**)。
- **处置**: 按「加文件 → 三份 `index.html` 的 `scripts` 各加一行 → `app.js` 补 `app.mixin(window.X)`」三步走完再跑守阵。**⚠ 第四处: `prism/index.html` 是 shell 体量上限 `210` 行的贴着线跑的那个**(atlas 203 / console 207 / prism 210, 2026-10-10 实测), 在 prism 加一行**必须先从别处腾一行** —— 腾一处多余空行即可(清单等价断言只看解析后的 manifest, 去掉空行不破坏等价, 也不会让三份 diff 失焦); **不要**去压行/合并 JSON 数组项。
- **守阵**: `_scan_mixin_wiring`(list/注入双向) + `test_frontend_static_bundle_health` 的 shell 行数上限。
- **复发**: 0

### 再拆前端大文件: 等价性验证 = 切割自验 + 真 API stub 冒烟 DOM 比对

- **触发**: 拆任何模板/样式/JS 大文件时(W1/W2a/W2b 已各有一套, 复用方法)。
- **判别**: 静态守阵抓不住**载入期**错误 —— 实测 W2b 切分脚本把原 `const app = createApp({` 残留造成双重声明, pytest 全绿而页面不挂载, 是 stub 冒烟的 `data-drv-mounted` 现形的。
- **处置**: ①程序化切割(解析器地标定切点 + 切点锚断言 + 多重集完整性自验), 不手抄; ②改造前先抓 DOM 基线, 改造后跑同一 stub(真 app.js + 最小 API: /api/config/public 免鉴权 + /api/state 定态 + /api/events 即回即关)比对渲染 DOM 逐字节等价(归一相对时间/脚本清单); ③工装是临时目录产物不入仓库(注入点适配见 [../testing/ui-preview-harness.md](../testing/ui-preview-harness.md))。
