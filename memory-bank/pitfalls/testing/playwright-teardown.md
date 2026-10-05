# Playwright webServer 收尾挂死: `spawnSync` 拉不起 `cmd.exe` ⇒ 杀不掉子进程, 端口不释放

> 摘要: 本工具 shell 里 `spawnSync` 全线 EBUSY(连全路径 `taskkill.exe`、不带 shell 都一样), 而 Playwright 停 webServer 用的正是 `spawnSync('taskkill … /T /F')` —— 失败被它 try/catch 静默吞掉, 子进程没死、stdio 管道关不掉, `waitForCleanup` 永不 resolve ⇒ 用例全 PASS 但命令永不退出、桩服务残留占着端口。
> 触发: dev.e2e 不退出, 测试全过但挂住, webServer 收尾, spawnSync EBUSY, cmd.exe EBUSY, taskkill 无效, 端口不释放, 桩服务残留, waitForCleanup, Playwright 挂死
**Refs:** memory-bank/tasks/26-10-06-test-playwright-e2e.md

### 用例全 PASS 但不打印汇总行、命令永不退出

- **触发**: 跑 `commands run dev.e2e`(桩服务由 `playwright.config.mjs` 的 `webServer` 托管), 用例逐条打了 `ok`,
  但没有 `N passed (Xs)` 那行, 命令一直挂着; 另开终端 `netstat -ano | grep <端口>` 见桩服务仍 `LISTENING`
  (2026-10-06 实测: 4/4 passed 之后挂死 4 分钟以上, 8137 上 python 仍 LISTENING)。
- **判别**: 先分清两种"不退出" —— ①**卡在收尾**(用例已全 PASS, 只缺汇总行)是本条;
  ②**卡在起服务**(一条断言都没跑, 报 `waitForFunction Timeout`)见 [smoke.md](smoke.md)「桩服务没起来」条。
  一条命令定位: `node -e "console.log(require('child_process').spawnSync('echo hi',{shell:true}))"`
  —— 打出 `error.code === 'EBUSY'`(指向 `C:\WINDOWS\system32\cmd.exe`)即命中。
- **机制**(读 playwright-core 源码确认): Playwright 停 webServer 等的是子进程的 `'close'` 事件,
  而 Node 的 `'close'` 要求**所有 stdio 管道都关闭**; Windows 上杀进程走
  `spawnSync('taskkill /pid <pid> /T /F', {shell:true})`, 非 Windows 走 `process.kill(-pid, SIGKILL)` 杀整个进程组
  (`detached: process.platform !== "win32"`)。`spawnSync` 一旦 EBUSY, 这一步被 Playwright 的 try/catch
  **静默吞掉** ⇒ 进程没死 ⇒ 管道关不掉 ⇒ `waitForCleanup` 永不 resolve。
- **处置**: 这是**工具 shell 的环境限制, 不是配置问题** —— `spawn`(异步)路径完全正常, 所以起桩服务 /
  启浏览器 / 用例执行全不受影响, 只有 `spawnSync` 挂。三条:
  ①**跑 e2e 用真实终端**(用户自己的 PowerShell / cmd), 别在 AI 工具 shell 里跑;
  ②已在工具 shell 里跑挂了 ⇒ 用 **bash 的** `taskkill //F //PID <netstat 查到的 PID>` 清残留
  (bash 里 `taskkill` 可用, 只有 node 的 `spawnSync` 不行);
  ③**别为此改配置** —— 加 `reuseExistingServer: true` 只是把"卡住"换成"验的是残留服务", 后者更糟(见 smoke.md)。
- **守阵**: 无 —— 判据依赖工具 shell 的 spawn 行为, 静态判不出。
