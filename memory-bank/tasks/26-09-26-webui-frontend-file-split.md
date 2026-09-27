# 26-09-26-webui-frontend-file-split — WEB UI 前端大文件拆分

**Status:** In Progress
**Added:** 2026-09-26
**Updated:** 2026-09-27
**Summary:** 用户报「webui 代码文件很大难维护」。实测定案单体 = 两套 index.html(2555/2613 行,根模板各约 2360 行语义同构副本)+ atlas/style.css 1720 + app.js 1271;后端与共享 JS 粒度健康不在范围。产出拆分计划(plans/26-09-26-2233),5 波次,机制定案「分片 HTML + boot.js fetch 注入」。2026-09-27 用户放行按计划实施、往「消灭双模板副本」走: W0 守阵迁移盘点 + W1 根模板分片已落地(两套 shell 166/177 行 + 14×2 分片全部 ≤400 行 + shared/boot.js,聚合字节等价 + 无头 Edge 冒烟通过,守阵全绿)。待: W2 样式/app.js 续拆、W3 双模板差异评估、W4 收口。

## 原始请求

> 目前的webui代码文件很大,难以维护,需要拆分,先列一个计划

## 思考过程与决策

- **量测先行**:shared JS 已按域拆 20 个文件(最大 app.js 1271),后端 2026-09-15 已拆(routes/ ≤221 行)⇒ 真正单体是**两套根模板**(atlas/prism 的 index.html,#app 模板各约 2360 行)与 atlas/style.css。两套模板语义同构(守阵 test_web.py:1113 原话「模板本就同构」)是「成对改」人肉纪律的根源。
- **机制选型(计划 §5 定案)**:候选三 —— ①JS 模板字符串分片:被否决,模板内已有 3 处反引号+`${}`(Vue 表达式里的 JS 模板串),嵌套必须转义且此后每次写模板都要记得 = 静默新坑源;②后端聚合端点:破坏「目录即 URL、静态零逻辑」;③**分片纯 HTML + shared/boot.js 顺序 fetch 注入 #app 后放行 createApp**:零转义、编辑器高亮、v-cloak 语义保留(注入前 #app 为空天然无闪烁),定案。
- **守阵爆炸半径(W0 处理)**:test_web.py 约 10 处断言直接读 index.html 全文(按钮 bt 计数、tpl-hub-field、挂件类名 `_scan_page_class_wiring`、页面位置、键盘接线等)——拆分必须连守阵一起迁移,方案是改扫「shell+分片聚合」。app.js 片段守阵先例(test_web.py:653-709 加载顺序+漏挂检查)直接复用其模式。
- **等价性验证**:ui-preview-harness(无头 Edge + 包装 createApp 捕 `window.__VM`)做拆分前 DOM 快照基线,逐波对比。

## 实现计划

见 [plans/26-09-26-2233-plan-webui-frontend-file-split.html](../plans/26-09-26-2233-plan-webui-frontend-file-split.html):
W0 守阵迁移方案+harness 基线(0.5 轮) → W1 根模板分片(2 轮,由小到大:dialogs→shows→torrents→groups→settings→topbar) → W2 样式/app.js 续拆(1 轮) → W3 双模板收敛评估(可选,默认只出差异报告) → W4 收口。合计 4.5–6 轮。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 现状量测 + 计划文档产出 + 自检 | ✅ |
| 2 | W0 守阵迁移方案 + 等价性基线 | ✅ (守阵迁移清单落地; 等价性基线改用「聚合字节等价 + 无头 Edge stub 冒烟」替代, 见进度日志 26-09-27) |
| 3 | W1 根模板分片(两套 UI + boot.js + 守阵升级) | ✅ |
| 4 | W2 atlas/style.css 分层 + app.js 续拆 | ◐ CSS 分层 ✅(style.css 留根 + css/{components,views,dialogs}.css, 字节等价); **app.js 续拆延后**(见进度日志 26-09-27 第 2 条) |
| 5 | W3 双模板差异评估报告(可选) | ✅ reports/26-09-27-1143-report-webui-template-diff.html —— 语义同一性 98.1%, 皮肤类名差异 0, 收敛高度可行, 待用户拍板是否实施 |
| 6 | W4 收口(基线/回写/真机冒烟/提交) | ⬜ (基线切片留待 W4; 本轮实测 test.full 口径 1686+1 全绿, TOTAL 91%) |

## 进度日志

- **2026-09-26 22:40**: 计划产出。P0 自检修一处(wave-id accent 一屏超 2 处 → 改 ink);HTML 标签配平机检过;plans/_index 经 kb.index 登记。**未提交**(等用户评审计划,可能调整波次后再随 W0 一并入库)。
- **2026-09-27 11:50**: 用户放行「按计划实施,往消灭双模板副本走」。**W0+W1 一个会话内落地**:
  - **W0 守阵迁移**(盘点 test_web.py 直读 index.html 的 13 处 → 全部改读「聚合」): `_app_bundle_files`(script 顺序改读 tpl-manifest 清单)、`_scan_mixin_wiring`(refs 补 shell 静态 boot.js 引用)、按钮体系 bt 计数、search-clear、HR 计数/字段、tpl-hub-field、批量右键、meta 对话框、add-drop、次级菜单、站点导入、HR 状态块(锚点扫描)。新增守阵 `test_frontend_template_split_wiring`: ①清单完整性(漏挂=红/挂不存在=红/into 非法=红) ②双 UI 分片名单同名同序 ③聚合标签配平(替代计划的"逐分片配平",见偏离记录) ④shell ≤200 行/单分片 ≤400 行体量守阵 ⑤清单脚本序(vendor 首 / app.js 尾)。no-cache 测试补 /atlas/tpl/topbar.html 与 /shared/boot.js 路径。
  - **W1 切割**(一次性工装脚本, 不入库): 两套 index.html → shell(head+sprite+#app 内联登录段+tpl-manifest 清单+boot.js 引用, 166/177 行) + `tpl/*.html` 14 分片/UI(topbar 224/240、groups 174/173、torrents 101、shows 210、ctx-menus 218/217、settings 210、settings-detail 270、statusbar 58/59、overlays 50/18、drawer 169/167、dialogs 217/105、dialogs-mgr 239/252、popovers 132/295、xtpl 139;双 UI 内容分组按各自文档序, 名单同名同序)。切割点按解析器地标定, **聚合字节等价自验通过**(shell 内联段 + app 桶分片按清单序拼接 == 原 #app 内部行; xtpl 分片 == 原 x-template 段)。
  - **shared/boot.js**(~100 行, 两套共用): 按 tpl-manifest 顺序 fetch 分片(app 桶注入 #app beforeend, body 桶注入 body)→ 全部成功才按序放行 21 个逻辑脚本(动态 script `async=false` + onload 链钉执行序);任一步失败显式错误占位(复用 login-mask 类名)并停止。
  - **无头 Edge stub 冒烟通过**(工装临时目录不入仓库): 真 shell+分片+boot.js, 探针 app.js 断言注入结构 —— 双 UI app 顶层 16/17 节点、template.content 恰 3 子区(sticky-head/layout/hub main)、视图模板在位、xtpl 注入 body、Vue+21 脚本依序加载、无错误占位。⚠ 探针两处误判均系 template 内容 inert(querySelector 进不去 `<template>` 内容/嵌套模板), 原版页面挂载前同样如此, 非产品问题。
  - **实测**: test_web.py 173 passed + 1 skipped(基线前值 1665+1 全量口径不变);test.quick 1684 passed + 1 skipped + **2 failed(远端 0f98e7a 自带** `26-09-26-2345-plan-commands-shipflow-v2.html` 缺 doc-topic/status/added/updated meta, 非本任务范围, 待用户定夺修复或入池)。
  - **计划偏离 2 条**(实施口径 vs 计划原文): ①「分片以平衡标签块为单位、逐片配平」→ 改为「有序字节切分 + 聚合配平守阵」: 实测根模板的 wrapper(`<template v-else>`/`.layout`/`.hb-wrap`)横跨计划要拆的视图边界, 逐片配平必改 DOM(违"零运行时行为变化"红线);聚合字节等价 + 聚合配平 + 聚合上跑全部既有内容断言, 覆盖同一风险面且更强。②「harness DOM 快照基线」→ 改为「聚合字节等价(比快照更强的等价证明)+ boot 机制 stub 冒烟」: 生成式切割使聚合与原文件逐字节一致, 快照对比失去对象;boot 时序风险(计划风险表最高项)由 stub 冒烟直接驱动验证。分片数 6 → 14(计划预估行数按实际翻倍, ≤400 行上限强制细分)。**未提交**(等用户说提交)。
- **2026-09-27 12:00 第二轮(用户: 补meta + 继续推进)**:
  - **范围外缺陷已修**(用户授权): `26-09-26-2345-plan-commands-shipflow-v2.html` 补 doc-topic=`commands-shipflow-v2` / doc-status=`Done`(实现随 0f98e7a 已落地) / doc-added / doc-updated → test_docs_forms 10 全绿。
  - **W2a atlas/style.css 分层落地**: 连续字节切片(级联序 = link 序) → `style.css` 留根(令牌+全局基线 200 行) + `css/components.css`(跨页组件 680) + `css/views.css`(页面区+响应式 402) + `css/dialogs.css`(对话框浮层 438), 全部 ≤700 行; shell head 链接 4 件; **聚合与 git 原版逐字节相等**(自验过)。守阵迁移 4 处直读 style.css → `_ui_css_aggregate`(按 shell link 序聚合, 单一来源); 分片守阵补 CSS 链接序 + ≤700 行体量断言。⚠ prism/css/views.css 804 行超 700 为既有状态, 不属本次范围(已记偏差)。
  - **W2b app.js 续拆延后**(决策): ①app.js 头部硬约束(2026-09-20 拆分定案)明确「轮询主链/HTTP 鉴权/视图切换留在内核」, 计划 W2 再拆属推翻该设计决定, 应显式拍板而非顺手改; ②实测成员分布: methods 426 行里 ≥25 行的大方法仅 6 个(~263 行), 只拆方法 app.js 仍 ~970 行, 达 ≤500 验收必须连 data(236)/computed(154)/watch(71)/顶层常量(380) 深拆 —— 全部是鉴权/轮询关键路径; ③现有 stub 冒烟用探针替换 app.js, 验证不到真内核运行时, 深拆需要先搭真 API stub 冒烟。**下一波入口**: 成员清单已盘好(methods 22 个/块界 381/618/773/845), 拆域建议 = 真值轮询(refresh)/启动引导(bootstrap+startEvents+_logout)/视图切换(setViewMode+doSearch) 三片段 + state 混入(data/computed 按域), 动手前先补真 API 冒烟工装。
  - **W3 差异评估报告落地**: reports/26-09-27-1143-report-webui-template-diff.html。方法 = 元素级对齐(按 v-if/结构标记配对, 消除两套 UI 弹窗文档序不同造成的分片组合错位假象) + SequenceMatcher + 三分类。**数据: 15 配对元素 12 个逐行全同; 全模板 ~4,300 行差异仅 80 行(语义同一性 98.1%), 皮肤类名差异 0 行**。真实分叉 = ①棱镜已上 FX-20/21/24 切胶囊、星图仍原生勾选框(addOpen/modal.visible, 绑定状态同名同义, 差异只在呈现组件) ②棱镜专属 col-ghost(FX-25)与主题切换器 ③注释措辞(结构差异大头)。**结论: 收敛高度可行**(条件 = 先拍板星图是否跟胶囊 + 守阵对象重写 + 双 UI 五主题冒烟矩阵; 工作量 1–2 轮), 待用户拍板。
  - **实测**: test.full 口径 **1686 passed + 1 skipped + 0 failed, TOTAL 91%**(2725 条副作用台账越界 0)。基线切片未立(计划把基线入库排在 W4 收口)。**未提交**(等用户说提交)。
- **2026-09-27 12:40 第三轮(用户拍板: 统一差异清单1-4全部 + 为后续差异留口) —— 单一语义模板收敛落地**:
  - **机制**: 两套 shell 的 tpl-manifest 全部改指 `/shared/tpl/*.html`(14 分片单一语义源), `atlas/tpl/` 与 `prism/tpl/` 双副本删除; boot.js 零改动(绝对路径 fetch)。模板级 UI 差异唯一入口 = `<template v-if="ui === 'atlas'|'prism'">` 条件块 + `ui-diff:` 注释标记, 守阵 `_scan_ui_diff_registry` 收集为「活差异清单」(当前恰 1 条: 棱镜主题切换器)。app.js 增 `ui` 数据字段(pathname 派生) + `uiSwitchTarget` computed(互切链接参数化, 模板不再各写一份 <a>)。
  - **差异清单 1-4 统一落点**: ①切换胶囊 —— 星图跟进棱镜 FX-20/21/24(atlas css 移植 .opt-pill 族/.add-dialog-opts/.modal-opts verbatim, 令牌面已同面零映射; .add-dialog-hint-warn 改 visibility 常驻占位), 统一模板取棱镜的 addOpen/modal 标记; ②棱镜专属 —— col-ghost 双端生效(JS 共享本就具备, 仅移模板块+CSS, atlas 顺带获得 FX-25 列头拖动虚影), 主题切换器走差异口条件块(棱镜 CSS 原有); ③注释 —— 取棱镜系(较新维护); ④结构小分叉 —— 随单一标记消失。atlas 死 CSS 按坑条目连带清(.modal-check 族/.add-dialog-check 族, 全语料验证零引用后删)。
  - **守阵升级**(test_frontend_template_split_wiring): ①双 shell 清单必须逐项相等(漂移=模板分裂回潮) ②残留 <ui>/tpl/ 目录=红 ③shared/tpl 孤儿分片=红 ④差异口注册表(取值只认 atlas|prism + ui-diff 注释必须存在, 注册表为空=红)。`_ui_aggregate`/守阵路径解析支持 /shared/ 绝对 src。
  - **实测**: test_web 173 passed; test.quick 1686 passed + 1 skipped + 0 failed; 无头 Edge 冒烟双 UI 全项通过 —— **两 UI #app 顶层节点 17/17 完全一致**(atlas 因 col-ghost 双端生效 16→17, 即统一的直接体现), 差异口条件块/xtpl/footer/toast/sticky/hub 全部在位, 无错误占位。
  - **发现未修(范围外)**: prism/css/components.css:247-251 残留死规则 .modal-check 族(prism FX-24 切胶囊时遗留, 统一模板零引用) —— 属棱镜侧既有死代码, 按范围守卫不入本波; 建议随下次 prism CSS 波次清理。**未提交**(等用户说提交)。
