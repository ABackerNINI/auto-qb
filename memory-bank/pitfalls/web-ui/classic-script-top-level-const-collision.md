# classic script 顶层 let/const 跨文件共享全局词法环境: 多文件同名顶层常量 = 全页面瘫

> 摘要: classic script(非 module 的 `<script>`)的顶层 `let/const` 不进 `window` 而是进**全局词法环境**, 所有 `<script>` 标签共享这一个环境 —— 两个文件各自写 `const FIT = ...`, 后装载的那个直接 `SyntaxError: Identifier 'FIT' has already been declared` 整份文件不执行; 而本项目的静态守阵全是**源码字符串比对**, 看不见这种"只在真实浏览器解析期暴露"的错, 结果是 mixin 未注册、整页瘫, e2e 每例对一个瘫页等 30s 超时, 看起来像"机器慢了"。
> 等级: L0
> 触发: 顶层 const 撞名, classic script 全局词法环境, SyntaxError, mixin 未注册, 白屏, AQB_OVERLAY_FIT, 静态守阵看不见, 多 js 文件同名常量, 顶层 let, let/const, 跨文件撞名
> 收口: 2026-10-22 07:05 全部别名收进**方法内作用域**(aq-tip IIFE 内合法), 新增第 5 类守阵 `test_webui_static_dom_panel.py::test_overlay_fit_single_point` 的跨文件顶层 const/let 撞名扫描(双文件变异红验); test.full 3999 passed / 2 skipped / 99%, e2e 全量 340 passed / 10 skipped 逐位持平(基线 26-10-22-0646)
**Refs:** memory-bank/tasks/26-10-22-webui-overlay-fit.md, memory-bank/testing/baselines/26-10-22-0646-webui-overlay-fit.md

### 多文件顶层同名常量 = 后装载的文件整份 SyntaxError, 静态守阵全绿而页面已瘫(2026-10-22 新记)

- **触发**: 给 7 个消费文件接同一个单点模块(`shared/overlay_fit.js` → `window.AQB_OVERLAY_FIT`)时, 图省事在每个文件**顶层**各写一句 `const FIT = window.AQB_OVERLAY_FIT;`。本项目 static 全是 classic script(非 module), 顶层 `let/const` 进的是**全局词法环境**(不是 `window` 的属性), 所有 `<script>` 标签共享 —— `config_hub.js`(manifest 中首个装载)声明成功, 后 6 个文件全部 `Identifier 'FIT' has already been declared`, 整份文件一行不执行。
- **判别**: ①**页面症状**与报错完全脱节: `window.AQB_*` mixin 没注册 → Vue 应用报 `Cannot read properties of undefined (reading 'props')`, Playwright `pageerror` ×6; ②**静态守阵不红** —— 本仓守阵以源码字符串比对/接线计数为主, "文件里有 `FIT`"恒真, 撞名只发生在浏览器解析期; ③**e2e 全量超时是强信号** —— 本轮此前每次 `dev.e2e` 都撞 1200s 包超时, 一度归因为"机器慢"; 真相是每例都在对一个瘫页 `waitForSelector` 等 30s, 10 个用例就把预算烧穿。⚠ 只要 e2e 从"逐例快速失败"变成"整批匀速超时", 先怀疑页面根本没起来, 别先怀疑机器。
- **处置**: ①别名**一律方法内声明**(`const FIT = window.AQB_OVERLAY_FIT;` 放进每个消费方法; IIFE 内部的顶层声明也是合法函数作用域, 如 aq-tip 的 `place()`), 或改用 `var`(挂 `window`, 后写覆盖前写而不报错——但覆盖会静默换值, 不推荐); ②根治纪律: **跨文件顶层只允许 `var`/函数声明(挂 window 可覆盖), 需要不可变绑定就必须收进函数作用域**; ③守阵补齐: 扫描 `static/shared/*.js`(排除 vendor)全部顶层 `const/let` 名, 跨文件重名即红 —— 这类错 node 静态检查(node --check 是逐文件的)也看不见, 只有"跨文件并读"才抓得到。
- **守阵**: `tests/test_webui_static_dom_panel.py::test_overlay_fit_single_point` 的跨文件撞名扫描(双文件变异红验过: 制造两个文件同写顶层 `const FIT` 断言转红); e2e 全量 340 passed / 10 skipped 为行为面兜底(此前正是 e2e 第一个暴露)。
- **复发**: 0 (新记)
