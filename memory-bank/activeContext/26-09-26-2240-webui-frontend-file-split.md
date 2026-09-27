# WEB UI 前端大文件拆分(W2b 内核拆分落地, W4 收口中)

> 摘要: W2b 落地 —— app.js 1281→411 行, 拆出 state.js/lifecycle.js(经 `...window.X` 展开进根组件选项, ❗不能走 app.mixin 否则波及 hub-field 实例)+ auth/polling/view 三个全局 mixin 方法域; 前置补齐真 API stub 冒烟工装, **渲染 DOM 改造前后双 UI 逐字节等价**(atlas/prism 28126/29696 字符)。收敛(shared/tpl + 差异口)同轮全绿复验。W4: 基线切片已入库(26-09-27-1305, TOTAL 91%), 知识库回写完成。实测 test.full 口径 1688 passed + 1 skipped + 0 failed。未提交。
> 触发: 内核拆分, app.js, 根选项展开, state.js, lifecycle.js, 真 API stub, DOM 等价, 基线切片
> 最后活动: 2026-09-27 13:10

## 状态

- **已完成**: W0 守阵迁移 / W1 模板分片 + boot.js / W2a 样式分层 / 单一语义模板收敛(shared/tpl + 差异口)/ **W2b 内核拆分**(5 片段 + 瘦身 + 守阵形态④ + 整包聚合读法)/ **W4 基线切片入库**。
- **待办**: 用户真机 qB 侧冒烟(五主题) / 提交(等指令)。
- **关键决策**: ①data/watch/生命周期走根选项展开、方法域走全局 mixin(hub-field 隔离是硬理由, app.js 头注释三条硬约束); ②等价验证 = 改造前后真 app.js stub 冒烟渲染 DOM 逐字节比对(强于快照); ③守阵成员查找一律整包聚合(_app_bundle_text/_bundle_iter)。
- **范围外发现**: prism/css/components.css:247-251 死规则 .modal-check 族(FX-24 遗留), 建议下次 prism CSS 波次清理。
