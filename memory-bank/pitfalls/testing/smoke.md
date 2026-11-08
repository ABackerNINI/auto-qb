# 浏览器冒烟 (Windows 上可做, 长期能力)

> 摘要: `scripts/ui_harness.py` + `e2e/`(@playwright/test)是本仓库覆盖前端渲染的唯一手段; 这里是它的环境坑与验证手法
> (部分条目源自旧单页冒烟脚本时代 —— 该脚本 2026-10-06 已退役, 判据对 e2e 新轨同样成立)。
> 触发: 浏览器冒烟, e2e, Playwright, Edge, 白屏, 前端改完, 时序复现, 聚合行状态色, Cannot find module playwright, 修饰键点击, Ctrl+click, 多选失败, site-chip, 点击落点, 落点验证 5 拍未过, 最后拦截者 (null), elementFromPoint, scrollIntoView, 行高于视口, sticky-head 拦截面, 3000 种子, 规模轮, 用例超时, 冒烟整体执行, stash 对照, 归因, 回归, 验错对象, 旧进程, 旧页签, 桩服务死了, 皮肤差异, prism 正常 atlas 异常, 服务端发出的字节, BASE_URL, does not provide an export named, 收集期 SyntaxError, 新增 spec 回潮
**Refs:** memory-bank/testing/baselines/26-10-29-0348-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-11-03-1053-ci-e2e-base-url-fix.md

## 规程单点(能力 / 门禁 / 启动)

- 能力定位、`npm run test:e2e:fast` 门禁、模式矩阵 env、桩服务用法与断言清单 → [../../testing/smoke.md](../../testing/smoke.md); 浏览器安装与版本对齐 → [../../testing/browser-env.md](../../testing/browser-env.md)。
- 旧「能力与定位」节(含 `scripts/e2e_selfcheck.py` 挂 `dev.e2e` 首条、单跑 `dev.e2e-check` 的开机自检)原文外迁: [attachments/smoke-capability-selfcheck.md](attachments/smoke-capability-selfcheck.md) —— 自检不过不进 spec 仍是现状。

### Playwright 从哪来: 优先仓库内 `node_modules`, 没有才挂 `NODE_PATH`

- **触发**: `Cannot find module 'playwright'`, 或版本不匹配报 `Executable doesn't exist`(2026-09-25 实测)。
- **判别**: 按优先级找包 —— ①**仓库内** `node_modules/playwright-core`(`require` 从 `scripts/` 向上解析先命中);
  ②没有 `node_modules` 的 clone(`node_modules/` **已 gitignore**, 不会跟着 clone 走)⇒ `NODE_PATH` 指仓库外一份;
  ③npx 缓存 `%LOCALAPPDATA%\npm-cache\_npx\<hash>\node_modules`(可能已空)。
- **处置**: 详细装法、`npm i --no-save` 补救与新 clone 报错错位的现场见 [attachments/smoke-playwright-install.md](attachments/smoke-playwright-install.md)。

### 桩服务没起来 / 起来的是**旧进程** ⇒ 冒烟整轮"整体执行超时", 看着像前端白屏

- **触发**: 跑 `commands run dev.e2e`(webServer 起 `scripts/ui_harness.py`)或手工起桩后跑 e2e, 报
  `冒烟整体执行 — page.waitForFunction: Timeout 30000ms exceeded`(或 `ERR_CONNECTION_REFUSED`)。
- **判别**: 冒烟第一条断言是"`.group-row` 出现", 桩没服务到当前代码它就超时, 症状与
  "前端模板写错导致白屏"**完全同形**, 极易误判成自己改炸了。两种成因都实测到过:
  ①**端口被占** —— uvicorn 只打一行 `[Errno 10048] …地址只允许使用一次` 就退出,
  而**旧进程仍在服务旧代码**(页面可能 `Not Found` 但 `curl /api/...` 仍 200 ⇒ 像"服务是好的");
  ②**后台进程随 shell 调用结束被杀** —— 用 `(cmd &)` 起的服务在本次 Bash 调用返回后就没了,
  下一轮冒烟 `ERR_CONNECTION_REFUSED`(而 `curl` 在**同一次调用内**是通的, 误以为服务活着)。
- **处置**: 常驻后台起桩、日志首行核对、`curl <base>/prism/` 判活、残留桩归属与端口取号现状见 [attachments/smoke-stub-service.md](attachments/smoke-stub-service.md)。

### 新增 spec 从 harness import `BASE_URL` ⇒ 收集期 SyntaxError, 一条 spec 拖垮全量收集

- **触发**: 跑全量 e2e(`commands run dev.e2e`)在**收集阶段**就崩(一条用例都没跑), 报
  `SyntaxError: The requested module './harness.mjs' does not provide an export named 'BASE_URL'`。
- **判别**: 2026-11-03 实证 —— 端口改 0 的机械替换(47a61c7c, 41 个 spec)只覆盖**当时存量**,
  之后新增的 `e2e/search-uncovered-no-duplicate.spec.mjs`(2a3e22db)照旧
  `import { BASE_URL } from './harness.mjs'`, 而 `harness.mjs` 早已只导出 `baseUrl()` 函数。
  ESM 具名导出缺失在**链接期**抛错, 与平台 / 浏览器无关 —— 本机跑同一命令同样必红;
  本地"绿"只是因为没跑全量收集(未执行 `--list`), CI 一收集就现形。
- **处置**: spec 一律 `import { baseUrl }` 并在**使用点**调用(`${baseUrl()}/...`) —— 端口要等
  webServer.wait 注入 `UI_HARNESS_PORT` 后才可读, 模块级常量恒 undefined。新增 spec 先跑
  `commands run dev.e2e -- --list` 收口。守阵: `tests/test_port_zero_guards.py::test_e2e_modules_use_lazy_base_url`
  扫 `e2e/` 全部 `.mjs`(`BASE_URL` 零命中) —— 原守阵只查 harness.mjs 的**定义侧**, 拦不住调用方回潮。

### 全量套件增长撞预算: `dev.e2e` 引擎 timeout / CI job timeout 到点强杀

- **触发**: `commands run dev.e2e` 报 `[FAIL] dev.e2e 超时(1200s) —— 卡住的全量 playwright 运行`
  (用例没跑完、也没失败清单), 或 GitHub Playwright job 在 20 分钟处被 canceled。
- **判别**: 2026-11-03 实证 —— 套件涨到 440 例后全量实测 21.9m(本机 CI=true 会 retry 1 次), 旧
  `dev.e2e` 预算 1200s 与 CI job `timeout-minutes: 20` 双双不够; 这不是用例挂起, 是预算顶满(看
  `--list` 能秒过、小范围能跑绿即可区分)。
- **处置**: 两处预算**同轮按 ≈2× 实测抬高并保持单点** —— `.commands/dev/config.toml` 的 `timeout`
  字段是引擎唯一读源(别在引擎/脚本里再写一个数字); 抬完用引擎加载器核对解析值
  (`_config.load_tree().tasks['dev.e2e'].timeout`) + 跑一次 `commands run dev.e2e -- --list` 证 task 可启动。
  套件再涨就该拆轮/与 CI 分工, 别再靠调数字顶。
- **2026-11-07 复核(第二次撞同一堵墙, 这次走拆轮)**: 套件涨到 450 例后 40m 预算再次顶满 —— 近 100 次
  run 93 cancelled / 0 success, 最后一条绿是 10-30(15m45s)。按实测 6.4s/例折算全量需 ≈48m, 抬预算
  已经抬过两轮(360s→600s→1200s→2700s / 20m→40m), 继续抬就是第三次。
  **正解是拆轮而非抬数字**: CI 改成日常 `@fast` 282 例分 3 片 + 量具 20 例独立 job(约 12-14m),
  全量 430+20 挂 `workflow_dispatch` 由 push 节流触发(实测 21m16s 跑完)。依据: 仓库早已落地 shard
  能力(`f8043824` 实测 2.62x), 只是 CI 没接线 —— 先看"仓库里是不是已经有更快的能力没用上"。
- **2026-11-07 新增判别(分片 setup 会吃掉 10 分钟)**: 同一批 5 片里, 4 片 setup 约 25s, 1 片
  `npm ci` 之后到 `Running N tests` 之间卡了 **9.5 分钟**(runner 侧 apt/浏览器依赖安装慢), 单片墙钟
  被拉到 21m。所以"每片 ≈ 例数 × 6.4s"只算了测试本身, 排 30m 护栏时要给 setup 留 8-10m 余量;
  若某片逼近护栏, 先看 setup 耗时而不是先怀疑用例挂起。

### 页面 hidden 态(VS Code 内置页 / 未 bringToFront)

- **触发**: 在隐藏页面上跑交互。
- **判别**: `document.hidden === true` 时 **rAF 完全不触发** ⇒
  ①`new Promise(r => requestAnimationFrame(...))` **永不 resolve**(工具报 deferred);
  ②Playwright `click()` 因拿不到两帧稳定盒模型**全部超时**;
  ③Vue `<Transition>` 停在 `enter-from`(元素在 DOM 里但 `opacity:0`)。
  读数也可能停在**旧布局**。
- **处置**: 先 `page.bringToFront()`, 等待用 Playwright 侧 `waitForTimeout`,
  交互一律 `dispatchEvent`; 截图前注入中和过渡类。

### 企业策略强装扩展(Dark Reader)会污染 headless

- **触发**: 颜色断言。
- **判别**: 即使 `--disable-extensions` + 全新 profile **照样注入并改写 CSSOM**。
- **处置**: **颜色断言必须读 `:root` 的自定义属性**而非元素 computed 背景;
  控制台错误过滤 `chrome-extension` 来源。
  ⚠ CDP 取自定义属性返回**原始书写值(hex)**不是 `rgb()`, 对比度计算要**先解析 hex**。

### `CSSStyleRule.cssRules` 在 Chromium 恒存在

- **触发**: 递归遍历样式表。
- **判别**: 它是**空 CSSRuleList**(真值)。
- **处置**: 必须按 `rule.type` 判定(MEDIA=4 / SUPPORTS=12)。

### Vue 3.5.13 取根实例

- **触发**: 想从控制台拿 Vue 实例。
- **判别**: `#app.__vue_app__._instance` **恒为 `null`**。
- **处置**: 用 `document.querySelector('#app')._vnode.component.proxy`。
  ⚠ 无头页里 Vue 实例**不在 window 上**(模块作用域), 只能操作 DOM。

### 页面每 2s 整表重渲染会让 Playwright 动作失败

- **触发**: "another element intercepts pointer events"。
- **判别**: 整表重渲染抢走点击。
- **处置**: `force: true` 或**断言优先取值**;
  `programmatic btn.click()` **不触发 form submit**(要 `dispatchEvent(new Event("submit"))`);
  断言即时色值可能取到 **transition 中间值** ⇒ 用**语义断言**。

### 整页白屏 = **包级失败**; 骨架在但某块空 = **模板表达式错误**

- **触发**: 页面白屏 / 某区域空。
- **判别**: `#app` 带 `v-cloak`, Vue 不 mount 就永远隐藏, 只剩背景;
  骨架在但某块区域空 = 模板表达式错误, **只能真机看页面**。
- **处置**: 定位**无需 node** —— 起静态服务 + 在 `page.addInitScript` 里挂
  `window.addEventListener('error', ...)` 拿 `filename:lineno`。
  静态扫描守阵见 `test_frontend_static_bundle_health`。

## 已外迁的条目(原文见附件)

- 冒烟整体执行 `elementHandle.click: Timeout` ≠ 桩没起来: HEAD stash 对照归因 — [attachments/smoke-attribution-and-gestures.md](attachments/smoke-attribution-and-gestures.md)
- 行内可交互后代会吞修饰键点击 / 行高于视口时 `scrollIntoView(center)` 把落点推出视口 — [attachments/smoke-click-and-geometry.md](attachments/smoke-click-and-geometry.md)
- 可复用的验证手法: 逐视图比对响应键、逐步喂时序复现竞态、聚合行状态色取色 — [attachments/smoke-verification-techniques.md](attachments/smoke-verification-techniques.md)
- 真实手势的前置条件: 拖拽收尾吞 click / 浮层离场动画拦截; 回归第一嫌疑是验错对象(旧桩/旧页签) — [attachments/smoke-attribution-and-gestures.md](attachments/smoke-attribution-and-gestures.md)
- Edge 同 `user-data-dir` 会单例移交(残留页面继续"幽灵操作") — [attachments/smoke-edge-singleton.md](attachments/smoke-edge-singleton.md)
- 一批环境怪象(`--window-size` 钳制 / `file://#anchor` 空白图 / 截图裁剪 / `--dump-dom` 单行 / `--headless=new` 挂起 / 注入路由被遮蔽) — [attachments/smoke-env-misc.md](attachments/smoke-env-misc.md)
