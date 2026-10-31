# 1688 passed + 1 skipped —— WEB UI 内核拆分(W2b): app.js 1281→411 行, 单一语义模板收敛复验

> 摘要: plans/26-09-26-2233 W2b+W4 收口轮。app.js 按域拆为 5 个内核片段: state.js
> (data/computed/watch)与 lifecycle.js(created/mounted/unmounted/updated)经 `...window.X`
> 展开进**根组件选项**(❗不走 app.mixin —— 全局 mixin 会波及 hub-field 实例, watch/mounted
> 双份执行), auth.js/polling.js/view.js 走既有全局 mixin 方法域范式; app.js 瘦身为常量 +
> 接线(1281→412 行)。验证链 = node 语法 + 整包接线守阵(形态④根选项展开) + 真 API stub
> 无头冒烟(改造前基线 vs 拆分后: 渲染 DOM 双 UI 逐字节等价, atlas/prism 28126/29696 字符)。
> 同轮复验单一语义模板收敛(shared/tpl + 差异口)全绿。
> 基线时间: 2026-09-27 13:05
> 档案: 26-09-26-webui-frontend-file-split

- **测试增量**: 总数不变(1688+1) —— 本轮为纯重构(零行为变化), 无新测试; 守阵扩展:
  `_scan_mixin_wiring` 接线形态 +④根选项展开(`...window.X`, 只认 app.js 内展开, 不放宽)、
  成员查找类守阵(页面持久化/展开态记忆/拖拽遮罩/次级菜单/COLS 单点/colManual 零残留)
  由单读 app.js 改为整包聚合读法(`_app_bundle_text`/`_bundle_iter`)。
- **拆分明细**: app.js 1281→411 行(常量单点 + 接线); state.js 294 / lifecycle.js 191 /
  auth.js 141 / polling.js 155 / view.js 122。成员逐行原样搬运(切点锚断言 + 多重集完整性
  自验通过)。

TOTAL 91%(11206 语句 / 815 未覆盖 / 3720 分支 / 330 partial; test.full 18.75s, 1 采样;
覆盖率口径见 [../baseline.md](../baseline.md))。
