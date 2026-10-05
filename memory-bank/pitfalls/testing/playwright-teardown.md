# Playwright webServer 收尾挂死: **带管道 stdio** 的 `spawnSync` 必 EBUSY => 杀不掉子进程, 端口不释放

> 摘要: 本机 node 的 `spawnSync` **只要带管道 stdio**(`'pipe'` 或默认)就 EBUSY —— `stdio: 'ignore'` / `'inherit'` 正常, 且与可执行文件无关(连 `process.execPath` 即 node.exe 自己都一样), 也**不是**文件句柄/杀软占用(重试 5 次 + 延迟全 EBUSY, 是确定性的, 不是竞态)。而 Playwright 1.63 停 webServer 用的正是 `spawnSync('taskkill /pid <pid> /T /F', {shell:true})`(**默认管道 stdio**) —— 失败被它 try/catch 静默吞掉, 子进程没死、stdio 管道关不掉, `waitForCleanup` 永不 resolve => 用例全 PASS 但命令永不退出、桩服务残留占着端口。
> 触发: dev.e2e 不退出, 测试全过但挂住, webServer 收尾, spawnSync EBUSY, 管道 stdio, taskkill 无效, 端口不释放, 桩服务残留, waitForCleanup, Playwright 挂死
**Refs:** memory-bank/tasks/26-10-06-test-playwright-e2e.md

### 用例全 PASS 但不打印汇总行、命令永不退出 [已修: `e2e/global-teardown.mjs`]

- **触发**: 跑 `commands run dev.e2e`(桩服务由 `playwright.config.mjs` 的 `webServer` 托管), 用例逐条打了 `ok`,
  但没有 `N passed (Xs)` 那行, 命令一直挂着; 另开终端 `netstat -ano | grep <端口>` 见桩服务仍 `LISTENING`
  (2026-10-06 实测: 4/4 passed 之后挂死 4 分钟以上, 8137 上 python 仍 LISTENING)。
- **判别**: 先分清两种"不退出" —— 1.**卡在收尾**(用例已全 PASS, 只缺汇总行)是本条;
  2.**卡在起服务**(一条断言都没跑, 报 `waitForFunction Timeout`)见 [smoke.md](smoke.md)「桩服务没起来」条。
  一条命令定位:
  ```
  node -e "const cp=require('child_process');for(const s of ['pipe','ignore','inherit']){const r=cp.spawnSync(process.execPath,['-e','process.exit(0)'],{stdio:s});console.log(s, r.error?r.error.code:'status='+r.status)}"
  ```
  —— 打出 `pipe EBUSY` / `ignore status=0` / `inherit status=0` 即命中。
  (**别**再用旧的 `spawnSync('echo hi',{shell:true})` 单点判据: 它只证明"带管道的 shell 调用失败", 容易被
  误读成"spawnSync 全线坏掉", 从而错误地推出"环境限制、只能换真实终端" —— 2026-10-06 第一版结论就是这么错的。)
- **机制**(读 playwright-core 1.63 `coreBundle.js` 的 `killProcess()` 确认): Playwright 停 webServer 等的是
  子进程的 `'close'` 事件, 而 Node 的 `'close'` 要求**所有 stdio 管道都关闭**; Windows 上它走
  `spawnSync(\`taskkill /pid ${pid} /T /F\`, { shell: true, windowsHide: true })` —— 没给 `stdio`, 即**默认管道**,
  于是必 EBUSY; 返回对象 `stdout`/`stderr` 为 `null`, 紧跟的 `.toString()` 再抛一次, 两者都被同一层
  try/catch **静默吞掉** => 进程没死 => 管道关不掉 => `waitForCleanup` 永不 resolve。
  非 Windows 走 `process.kill(-pid, SIGKILL)` 杀整个进程组, **没有**这个问题(CI 是 ubuntu-latest)。
  另: webServer 的 `attemptToGracefullyClose` 在 win32 上**直接抛** `"Graceful shutdown is not supported on
  Windows"`, 被 `.catch(() => killProcess())` 接住 —— 所以 `webServer.gracefulShutdown` 选项在 Windows 上
  根本走不到, **不能**指望它绕开这条路。
- **处置**: 已修 —— 新增 `e2e/global-teardown.mjs` 并在 `playwright.config.mjs` 挂 `globalTeardown`:
  用**异步** `exec`(走 spawn, 不受管道 stdio 限制)对 `netstat -ano` 里监听该端口的 PID 执行
  `taskkill /PID <pid> /T /F`, 再轮询到端口真正释放。执行顺序由 Playwright 的 task runner 保证:
  `createGlobalSetupTasks` 把全局 teardown 任务注册在 plugin setup **之后**, 而 teardown 按注册的**逆序**
  跑 => 本函数先于 webServer plugin 的 teardown; 等轮到它 `killProcess()` 时 `processClosed` 已为 true,
  整段 force-kill 被跳过。非 Windows 是 no-op。**实测: 修前挂死 4 分钟以上不退出; 修后
  `commands run dev.e2e` 14.8s / exit 0, 打印 `4 passed (12.3s)`, 8137 无 LISTENING、无残留 ui_harness 进程。**
- **实测数据**(2026-10-06, 本机):
  | 项 | 值 |
  |---|---|
  | `spawnSync` + `stdio:'pipe'`(默认) | `EBUSY`, 连 `node.exe` 自己都一样 |
  | `spawnSync` + `stdio:'ignore'` / `'inherit'` | `status=0` |
  | 重试 5 次 + 200ms 间隔 | 5/5 仍 EBUSY(确定性, 非竞态) |
  | 异步 `spawn` / `exec` | 正常 |
  | 异步 `taskkill /PID <listen-pid> /T /F` 后子进程 `'close'` | 929ms 触发, 端口释放 |
- **别踩的坑**: 曾据"spawnSync 全线 EBUSY"推出"环境限制、配置层修不掉、只能在真实终端跑" —— **该结论已作废**。
  判据下得早(只测了一种带管道的调用形态)、且把"某条调用形态失败"升格成了"整个 API 不可用"。
  遇 EBUSY 这类**语义宽泛**的错误码, 先把**变量**拉开逐个试(`stdio` 三态 / 带不带 shell / 换可执行文件),
  再下"是不是环境限制"的结论。
- **守阵**: 无 —— 判据依赖本机 node 的 spawn 行为, 静态判不出。
