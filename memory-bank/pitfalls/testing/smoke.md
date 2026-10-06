# 浏览器冒烟 (Windows 上可做, 长期能力)

> 摘要: `scripts/ui_harness.py` + `e2e/`(@playwright/test)是本仓库覆盖前端渲染的唯一手段; 这里是它的环境坑与验证手法
> (部分条目源自旧单页冒烟脚本时代 —— 该脚本 2026-10-06 已退役, 判据对 e2e 新轨同样成立)。
> 触发: 浏览器冒烟, e2e, Playwright, Edge, 白屏, 前端改完, 时序复现, 聚合行状态色, Cannot find module playwright, 修饰键点击, Ctrl+click, 多选失败, site-chip, 点击落点, 用例超时, 冒烟整体执行, stash 对照, 归因

### 能力与定位

- **触发**: 改任何前端渲染逻辑。
- **判别**: 能力 = `scripts/ui_harness.py`(真 create_app+QbManager+FakeClient+合成种子+命令泵,
  由 `playwright.config.mjs` 的 webServer 托管) + `e2e/` 七个 spec(@playwright/test, 双皮肤,
  按断言块拆分)。前端渲染**pytest 覆盖不到** ⇒ **改前端必跑 `npm run test:e2e:fast`(@fast 门禁);
  触碰乐观 UI/菜单/列设置加跑对应 spec; 全量矩阵轮收尾/排障串行人跑**。
- **处置**: 模式矩阵 env 参数化(计划 26-10-06-0708 §3.2)—— `E2E_CMD_RESULT=ok|error|hang` /
  `E2E_SKIP_CHECK=on|off` / `E2E_HR_SCENE=on|empty|off` / `E2E_TORRENTS=N`, 每轮独立起桩
  (六行命令见 `.commands/dev/config.toml` 的 `dev.e2e` note)。

### Playwright 从哪来: 优先仓库内 `node_modules`, 没有才挂 `NODE_PATH`

- **触发**: `Cannot find module 'playwright'`, 或版本不匹配报 `Executable doesn't exist`(2026-09-25 实测)。
- **判别**: 按优先级找包 —— ①**仓库内** `node_modules/playwright-core`(`require` 从 `scripts/` 向上解析先命中);
  ②没有 `node_modules` 的 clone(`node_modules/` **已 gitignore**, 不会跟着 clone 走)⇒ `NODE_PATH` 指仓库外一份;
  ③npx 缓存 `%LOCALAPPDATA%\npm-cache\_npx\<hash>\node_modules`(可能已空)。
- **处置**: ①仓库内 `node_modules` 在(clone 后 `npm ci` / `npm i` 一次)⇒ `commands run dev.e2e` 直接可用,
  什么都不用设(`package.json` 列了 `@playwright/test@1.63` 作 devDependency, npm 解析不认 `NODE_PATH`);
  ②没有 node_modules 的 clone ⇒ `npm ci`(有 lock)或 `npm i`, **别走旧轨的 `NODE_PATH` 挂载**
  (❗ESM 的 `import` 不认 `NODE_PATH` —— 旧单页脚本是 CJS 才用得了它, e2e 轨道一律走 npm 解析);
  版本对齐 `@playwright/test@1.63` ↔ `chromium-1243`;
  换不到退回 `chromium.launch({channel:"msedge"})`(**Edge 恒可用**)。
  复发: 1 —— 2026-10-02 npx 缓存已空(只剩空 hash 目录; 浏览器二进制 chromium-1243 仍在
  `%LOCALAPPDATA%\ms-playwright`) ⇒ 当时改用**仓库外**一次性 `npm i playwright-core@1.63`
  (如 `~/.aqb-smoke-deps`); 2026-10-06 起仓库内已有, 这条降为备选。

### 桩服务没起来 / 起来的是**旧进程** ⇒ 冒烟整轮"整体执行超时", 看着像前端白屏

- **触发**: 跑 `commands run dev.e2e`(webServer 起 `scripts/ui_harness.py`)或手工起桩后跑 e2e, 报
  `冒烟整体执行 — page.waitForFunction: Timeout 30000ms exceeded`(或 `ERR_CONNECTION_REFUSED`)。
- **判别**: 冒烟第一条断言是"`.group-row` 出现", 桩没服务到当前代码它就超时, 症状与
  "前端模板写错导致白屏"**完全同形**, 极易误判成自己改炸了。两种成因都实测到过:
  ①**端口被占** —— uvicorn 只打一行 `[Errno 10048] …地址只允许使用一次` 就退出,
  而**旧进程仍在服务旧代码**(页面可能 `Not Found` 但 `curl /api/...` 仍 200 ⇒ 像"服务是好的");
  ②**后台进程随 shell 调用结束被杀** —— 用 `(cmd &)` 起的服务在本次 Bash 调用返回后就没了,
  下一轮冒烟 `ERR_CONNECTION_REFUSED`(而 `curl` 在**同一次调用内**是通的, 误以为服务活着)。
- **处置**: ①起桩服务用**常驻后台任务**(`run_in_background`)—— `ui_harness.py` **长驻**(uvicorn.run 阻塞),
  别指望 `dev.harness` 会返回; 不要 `(cmd &)`;
  ②起完**立刻看 harness 日志首行**(打印监听地址与种子/组数), 端口被占就换端口;
  ③怀疑服务不对先 `curl <base>/prism/` 必须 200(只 `curl /api/...` 会被旧进程蒙过去)。
  复发: 2 —— 2026-09-28 多 clone 下 8099 被别会话残留 harness 占用, 换 `--port` 即过(路由没到本文件); 勿杀占用进程。
  2026-10-03 本会话开工 8099 再次被残留 harness 占用 —— netstat 现查 + 换端口零损耗, 判据(查监听 + curl 页面而非 /api)直接命中。
  复发: 3 —— 同日变体: 直接**复用**了 8099 残留服务做交互探针, 改完代码验证"全 PASS"其实验的是**别的 clone 的旧代码**
  (多 clone 工作区下残留 harness serve 的是它自己 clone 的静态目录; 12 项探针在旧代码上照样大半通过, 假信心比超时更危险)。
  判据: 怀疑服务归属时 `page.evaluate` fetch 静态 JS 比对特征串(如刚加的方法名), 不在 ⇒ 服务不是本 clone 的。
  处置: 改代码验证类冒烟**一律自己起桩**(后台任务 + 新端口), 残留服务只读不验。

### 「冒烟整体执行 — elementHandle.click: Timeout」≠ 桩没起来 —— 归因先做 HEAD stash 对照

- **触发**: 双皮肤冒烟在同一用例位置报 `冒烟整体执行 — elementHandle.click: Timeout 30000ms exceeded`
  (2026-10-03 实测: 追剧集行 Ctrl+click 块, position {8,8} 落点被 `sticky-head`/`header.topbar`/`html`
  交替拦截, Playwright 重试 30s 耗尽; 3 轮双皮肤 + HEAD 对照 4/4 复现)。
- **判别**: 与上一条「桩没起来」**同名词不同因** —— 上一条卡在首条 waitForFunction(页面根本没渲染,
  症状像白屏); 本条页面全程活着、断言一路 PASS 到超时点(看最后一条 PASS 在哪即知中断位置)。
  是否存量: 把自己的脚本改动 `git stash push -- <脚本>` → 跑一轮 → `git stash pop`,
  HEAD 同位置同报错即与本轮改动无关(实测 stash 前后失败点逐字一致)。
- **处置**: ①先跑对照再动代码 —— 命中存量 flaky 不顺手修, 记录位置与签名即可;
  ②超时中断该皮肤后续断言(含末尾 console.error 总检), 汇报写"中断点之前全部通过"而不是"冒烟全绿"。
  本条暂无守阵(点击拦截面随布局漂移, 静态判不出)。
  复发: 1 —— 2026-10-04 HR 历史表③ S5 三皮肤冒烟 3/3 复现(追剧集行 Ctrl+click 块同位置同签名),
  按本条目做 HEAD 档案对照 4/4 实锤存量; 为什么没命中: 本轮桩走查按既有处置口径①绕行未修
  (命中存量不顺手修, 只记位置与签名)。

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

### 其它环境坑(一批)

- **触发**: 冒烟环境相关的怪现象。
- **判别 / 处置**:
  · `--window-size` 在 Windows 被**最小窗口宽度钳制**(要验真窄屏就外层包 **iframe**);
  · `file://...#anchor` 截中间区块得到**空白图**(注入 `display:none` 把目标顶到首屏);
  · 整页截图 + PIL 自动裁剪在有**平铺底纹 / 渐变**的页面上失效;
  · `--dump-dom` 里顶层 DOM 是**整整一行**(按行 grep 全落空);
  · `--headless=new` 在本环境曾**挂起**(回落 legacy);
  · **注入路由必须插到 `app.router.routes` 最前**(否则被 `StaticFiles` 挂载遮蔽返回 404);
  · 注入脚本必须放 `<head>`(在 app.js 读 localStorage **之前**)。

### Edge 同 `user-data-dir` 会单例移交

- **触发**: 反复起冒烟服务。
- **判别**: 新进程**立即退出**, `/json/list` 拿到**旧实例的旧页面**;
  且**残留页面的轮询会在新服务起来后自动重连并继续执行"幽灵操作"**(实测把新环境里同名组删了)。
- **处置**: 每轮**独立 profile**; 起服务前按命令行过滤清 smoke edge
  (`CommandLine -match "edge-smoke"`, **不能全杀 msedge**), 并确认端口无监听
  (kill 后端口释放有延迟, 立即重启必 **10048**)。
  收尾用 **PowerShell** 关端口(`Get-NetTCPConnection -LocalPort N` → `Stop-Process`):
  `uv run python` 是**父子进程**, 按 netstat 的 PID 杀经常**杀不掉父进程** ⇒
  新桩服务 bind 失败而旧服务继续应答 ⇒ **你以为换了参数, 实际还在用旧服务**。

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

### 行内可交互后代会吞修饰键点击, 冒烟点行必须避开交互后代落点

- **触发**: 冒烟用例对行做 Ctrl+click 多选(或任何要点到"行本体"的动作), 落点用行几何中心(2026-10-01 实测, issue 26-09-30-0602 清偿)。
- **判别**: 行中部被行内可交互后代占据 —— 追剧集/辅种组行都有 `.site-chip`(`@click.stop="filterFromChip(...)"`, tpl/shows.html / tpl/groups.html), 点击落在芯片上时事件被 `.stop` 吞掉, 行 handler(selection.js `_toggleUnit`/`toggleGroupSel`)**根本不触发**, 症状是"修饰键点击不生效/选中 0 项", 极易误判成轮询重渲染竞态或真实 UI 缺陷。定案用仪器化探针: document **捕获级**记录 mousedown/mouseup/click 落点 + 覆写行 vm 方法看是否被调 + 行 DOM expando 查脱挂 —— 落点全在芯片、行 handler 未被调、节点未脱挂 ⇒ 是落点被吞, 不是竞态也不是产品缺陷。**间歇性**的来源: 芯片布局随前序冒烟步骤(状态文案/筛选态)漂移, 行几何中心有时被盖住有时不被 ⇒ 同一用例忽红忽绿。
- **处置**: 修饰键点击落点避开交互后代 —— `position: { x: 8, y: 8 }` 落**行左缘名称列**(`.g-name`/`.g-name-text` 无任何 `.stop` 后代); 右键不受影响(chip 无 `contextmenu.stop`, 事件冒泡到行)。修法已随 0602 清偿落码(旧冒烟脚本 commit `59725443`, 现由 `e2e/multiselect-shows.spec.mjs` 承载); 新写用例点行时照此选落点, 别默认几何中心安全。

### 整页白屏 = **包级失败**; 骨架在但某块空 = **模板表达式错误**

- **触发**: 页面白屏 / 某区域空。
- **判别**: `#app` 带 `v-cloak`, Vue 不 mount 就永远隐藏, 只剩背景;
  骨架在但某块区域空 = 模板表达式错误, **只能真机看页面**。
- **处置**: 定位**无需 node** —— 起静态服务 + 在 `page.addInitScript` 里挂
  `window.addEventListener('error', ...)` 拿 `filename:lineno`。
  静态扫描守阵见 `test_frontend_static_bundle_health`。

### 验证手法(可复用, 比静态阅读快)

- **触发**: 怀疑"某个键在某个视图下缺了"。
- **判别**: 起桩服务(`--torrents 300 --port <空闲端口>`, 合成种子自带非零 `dlspeed`/`upspeed`),
  再 `curl "…/api/state?view=<X>"` **逐视图比对响应键与合计** ⇒ 一眼看出哪个键缺了。

### 时序型缺陷可以在浏览器里"逐步喂时序"复现, 不必等真机

- **触发**: 竞态 / 时序类缺陷(2026-09-21 实测, 首次用它抓到"灰→绿→灰")。
- **判别**: 把缺陷拆成几个**有序时刻**, 每步直调一次前端方法并当场读结果
  (`vm.applyOptimistic(h, "pause")` → `vm.resolveOptimistic(h, true)` → `vm.onTruthEvent({truth})`),
  需要"服务端那一版数据"时用 `page.route("**/api/state*")` 拦截改成**我要的那一版**
  (如把成员 `kind` 改回命令前 + `rid` 前进), 再调 `vm.refresh()`。
  好处: 真机上要碰运气等的竞态(直查比快照新 ≤1.5s)在这里是**确定性的**, 且改前/改后的对照能跑成 1 秒一次的回归。
  ⚠ 两个坑: ①`page.route` 的回调是 **Node 侧**代码, 别在里面写 `${...}` 模板插值;
  ②`rid` 门控下服务端可能**不回数组**(`updated:false`), 拦截到空载荷时要**先补一次不带 `rid` 的全量请求**再改。
- **处置**: 按上述逐步喂时序。

### 在真浏览器里验"聚合行状态色"必须让注入的合成组落在**渲染窗口内**

- **触发**: 想验组 / 集行的状态色(2026-09-21 实测)。
- **判别**: 组 / 集表是**窗口化 + 客户端排序**的(只渲染视口附近 ~26 行, 默认按 `added_on` 降序)⇒
  把合成组 `prepend` 进 `vm.groups` 只会让它排在**窗口外**,
  `document.querySelector('[data-key=…]')` 拿到 `null`(第一轮就踩了, 差点把"没渲染"读成"没生效")。
- **处置**: 给注入组一个**极大 `added_on`**(如 `4102444800`)即可置顶。
  取色用 `getComputedStyle(el.querySelector('.g-name-text')).color` ——
  **组行没有 `.state-text` 列**, 整行靠 `.group-row.s-<kind> .g-name-text` 那条规则着色
  (做种绿 `rgb(23,138,92)` / 暂停灰 `rgb(82,112,140)`)。
