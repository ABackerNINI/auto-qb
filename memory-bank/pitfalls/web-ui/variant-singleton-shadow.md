# 变体内局部变量遮蔽单点 T/R/H: helpers 调用对数字取属性抛 TypeError, 渲染回落 classic

> 摘要: 详情面板变体文件头把核心层三件套收进模块级单点(`const T = reg.dtHtml` / `const R = reg.dtRaw` / `const H = reg.helpers`), 变体函数内再声明同名局部即遮蔽 —— dt12「空间树图」的 layoutMap 曾把局部 H 声明成 `mapEl.clientHeight`, 同函数尾 `H.rowFocusKey(...)` 对数字取属性抛 TypeError(2026-10-09 用户报障「选择空间树图后无显示、切换种子后回到经典」): 树图块只在 layoutMap 里绘制故永远空白, 抛错经核心 `_dtRender` catch 走「渲染抛错回落 classic」分支把该页签选择复位并落盘, 用户选择跨会话静默丢失。守阵 `test_drawer_tpl_variant_no_singleton_shadowing` 全禁: 凡变体声明了 T/R/H 单点, 该名在全文件(单点声明行外)禁止再被任何声明语句绑定(含多声明符列表 `let a = 1, H = 2` 与解构); 未声明单点的名不查(15 号无 H 单点, 其局部 H=22 合法)。写变体代码时局部名一律另起(如 mapH/RH), 注释里复述根因也要避开声明形态(守阵扫的是文件原文, 注释含 `const ... H =` 同样自证违例)。
> 触发: 改 drawer_tpl 变体, 写变体局部变量, 空间树图不显示, 选模板无显示, 换种子回到经典, 模板选择被重置, H.rowFocusKey is not a function, TypeError, 遮蔽, shadowing, dt12, layoutMap, squarify, 树图空白, 回落 classic, render failed fallback
**Refs:** memory-bank/pitfalls/web-ui/template-render.md · memory-bank/pitfalls/web-ui/vif-host-node-stale.md

## 条目

- 2026-10-09 用户报「WEBUI种子详情内容页空间树图异常: 选择后无显示, 切换种子后回到经典」。根因 = `12-content-space-treemap-collapsed.js` layoutMap 第 294 行局部 `H`(clientHeight)遮蔽第 24 行 helpers 单点, 第 326 行 `H.rowFocusKey(mapEl, "data-blk")` 对数字取属性抛 TypeError。两条可见症状同一根因: ①图块只在 layoutMap 绘制, 抛错即无块(选择后无显示); ②数据落袋/换种子走 `_dtRender`, catch 分支复位 `drawerTplSel.content = "classic"` 并落盘(换种子后回到经典、且刷新后仍是经典)。修复 = 局部改名 mapW/mapH; 同文件 squarify 的局部 H(无爆雷但属同坑类)一并改名 RH 让守阵不变式无例外; 新增守阵 `test_drawer_tpl_variant_no_singleton_shadowing`(tests/test_webui_static_dom_panel.py)。为何没被既有守阵抓到: 变体真跑类守阵只盖 dtHtml 转义/register fail-fast/回落分支四要素, 没有「变体渲染成功路径逐函数真跑」的电池, 静态守阵也没盯单点遮蔽 —— 本守阵补后者, 前者(逐变体 node 真跑)仍是缺口, 变体再加复杂几何函数时应优先补真跑。
