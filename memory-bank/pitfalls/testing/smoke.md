# 浏览器冒烟 (Windows 上可做, 长期能力)

> 摘要: `ui_harness.py` + `ui_smoke.cjs` 是本仓库唯一能覆盖前端渲染的手段; 这里是它的环境坑与验证手法。
> 触发: 浏览器冒烟, ui_smoke, Playwright, Edge, 白屏, 前端改完, 时序复现, 聚合行状态色, Cannot find module playwright, NODE_PATH, npx 缓存

### 能力与定位

- **触发**: 改任何前端渲染逻辑。
- **判别**: 能力 = `ui_harness.py`(真 `create_app`+`QbManager`+`FakeClient`+合成种子+命令泵)
  + `ui_smoke.cjs`(Playwright, 双 UI 断言 + 内置 A/B)。前端渲染**pytest 覆盖不到** ⇒ **改前端必做冒烟**。
- **处置**: `ok`(看正向)与 `--expect-cmd error`(看回滚)两种模式都要跑。

### Playwright 从哪来: 本 clone 无 `node_modules` ⇒ 挂 **npx 缓存**的 `NODE_PATH`

- **触发**: `Cannot find module 'playwright'`, 或版本不匹配报 `Executable doesn't exist`(2026-09-25 实测)。
- **判别**: `node_modules` **不在 `.gitignore` 里** ⇒ 就地 `npm i` 会污染 git status; 而 playwright
  已在 **npx 缓存**(`npx --no-install playwright --version` 有版本号就是它)。
- **处置**: `NODE_PATH='…\_npx\<hash>\node_modules' node scripts/ui_smoke.cjs --base …`
  (❗ESM 的 `import` 不认 `NODE_PATH`, 冒烟脚本必须 CJS); 版本对齐 `playwright-core@1.63` ↔ `chromium-1243`;
  换不到退回 `chromium.launch({channel:"msedge"})`(**Edge 恒可用**)。

### 桩服务没起来 / 起来的是**旧进程** ⇒ 冒烟整轮"整体执行超时", 看着像前端白屏

- **触发**: 起 `scripts/ui_harness.py` 后跑 `ui_smoke.cjs`, 报
  `冒烟整体执行 — page.waitForFunction: Timeout 30000ms exceeded`(或 `ERR_CONNECTION_REFUSED`)。
- **判别**: 冒烟第一条断言是"`.group-row` 出现", 桩服务没服务到当前代码时它会超时, 症状与
  "前端模板写错导致白屏"**完全同形**, 极易误判成自己的改动炸了。两种成因都实测到过:
  ①**端口被占** —— uvicorn 只打一行 `[Errno 10048] …每个套接字地址只允许使用一次` 就退出,
  而**旧进程仍在服务旧代码**(旧代码可能连 `/prism/` 路由都没有 ⇒ 页面是 `{"detail":"Not Found"}`,
  `curl /api/...` 却仍 200 ⇒ 看着"服务是好的");
  ②**后台进程随 shell 调用结束被杀** —— 用 `(cmd &)` 起的服务在本次 Bash 调用返回后就没了,
  下一轮冒烟是 `ERR_CONNECTION_REFUSED`(而 `curl` 在**同一次调用内**是通的, 于是误以为服务活着)。
- **处置**: ①起桩服务用**常驻后台任务**(`run_in_background`)—— `ui_harness.py` 是**长驻**的(uvicorn.run 阻塞),
  别指望 `dev.harness` 会返回; 不要 `(cmd &)`;
  ②起完**立刻看 harness 日志第一行**(它会打印实际监听地址与种子/组数), 端口被占就换端口;
  ③怀疑服务不对时先 `curl <base>/prism/` —— 必须 200(只 `curl /api/...` 会被旧进程蒙过去)。

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
