# 26-09-28-webui-settings-back-nav — WEBUI 设置二级页返回优化: 吸顶返回条(方案一) + Esc 返回(方案三)

**Status:** In Progress
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 设置二级页原唯一回首页入口是随页滚走的 12.5px 小面包屑, 且顶栏「设置」钮(openSettings)不重置 hub.view(分区持久化) —— 分区深处无任何路径回设置首页。三案比选后拍板方案一+三: ①面包屑升级吸顶返回条(--head-h 实测偏移 + 玻璃底抄 .hb-actbar, z-index 6) ②Esc 职责链尾追加返回首页(hubOnKey, dialogs.js::escBusy 同名单守门不抢 lifecycle 关闭链)。方案一为最简版待用户调整定稿; 键盘快捷键引擎(26-09-28-0354)落地时 Esc 分支须对账移植。
**Topics:** webui-settings-back-nav
**Refs:** memory-bank/tasks/26-09-28-webui-keyboard-shortcuts.md

## 原始请求

「WEBUI设置的返回方式优化, 比如点进"常规"页面中不太好返回到设置主页上, 设计3种返回方式供挑选」。三案预览比选后用户拍板: 「方案一三, 方案一先出一个简单的模板, 调整后决定」。

## 思考过程与决策

- **痛点取证**: ①二级页唯一回首页入口 = 页顶 12.5px 面包屑(hb-crumb), 随页滚走; ②`openSettings`(config_editor.js:211)只切 page 不重置 hub.view, 而 hub.view 持久化(localStorage `autoqb.ui.hub`) → 在分区里点顶栏「设置」仍停在原分区。
- **三案比选**(AskUserQuestion ASCII 预览): A 吸顶返回条(纯 CSS sticky, 零 JS)/B 悬浮返回球(滚过页头淡入 FAB, 需显隐 JS + 三皮肤核色)/C Esc 键返回(几行 JS, 键帽提示兜可发现性)。
- **吸顶口径**: top 用现成 `--head-h`(columns.js ResizeObserver 实测 .sticky-head 写入 :root, 设置页=纯顶栏高), -1px 防透缝与 .group-head 同口径; 玻璃底配方抄 .hb-actbar(--glass + backdrop blur); z-index 6 —— 只需盖过普通内容, 说明浮窗(60)/保存条(40)/抽屉一族(80)都在其上; `.content` 的 overflow-x: clip 不破坏 sticky(.group-head 先例)。
- **Esc 守门**: lifecycle.js 的 Esc 关闭链与 config_hub::hubOnKey 是同一 keydown 的并存监听, 直接在链尾加返回会让「按 Esc 关弹窗」顺带导航回首页。新增 dialogs.js::escBusy()(关闭链同名单, 顺序无关只看有无), hubOnKey 优先级: 说明浮窗 → 站点搜索清空 → `page==='settings' && view!=='hub' && !escBusy()` 才 hubBack(); lifecycle 链头与 escBusy 互留「新增浮层两处同步」注释。
- **样式单点**: .hb-crumb 只在 shared/console_hub.css 定义, 三皮肤(atlas/console/prism)同载一份, 颜色全走令牌(prism 亮色主题同成立)。

## 实现计划

方案一最简版已落地(5 文件): tpl/settings.html 返回条结构(← 箭头整钮 + 右端 Esc 键帽)、console_hub.css sticky 样式、config_hub.js hubOnKey Esc 分支、dialogs.js escBusy、lifecycle.js 链头互指注释。待用户试后调整: 条高/玻璃透明度/箭头样式/键帽文案; 定稿后再议方案二(悬浮球)是否叠加。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 三案设计与比选(AskUserQuestion 预览) | Done (26-09-28) |
| 2 | 方案一最简版 + 方案三 Esc(5 文件, test.full 1831 passed) | Done (26-09-28) |
| 3 | 用户试看调整 → 方案一定稿 | In Progress |
| 4 | 遗留: 顶栏「设置」钮是否重置回设置首页 | Open |
| 5 | 与键盘快捷键引擎对账(计划 26-09-28-0354 落地时, Esc 唯一 fixed 口径) | Open |

## 进度日志

- 2026-09-28 22:01 方案一最简版 + 方案三落地: test.quick / test.full 均 1831 passed / 3 skipped(基线 26-09-28-2201); 静态文件磁盘直读, 刷新即见效。回写件随主提交入库。
