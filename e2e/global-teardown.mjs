/**
 * Playwright `globalTeardown` —— webServer 收尾兜底 (Windows 专有)。
 *
 * 为什么需要它 (2026-10-06 实测, 不是推测):
 *   Playwright 1.63 停 webServer 走 `killProcess()` -> `spawnSync('taskkill /pid <pid> /T /F',
 *   { shell: true, windowsHide: true })`, **默认 stdio = 'pipe'**。而本机 node 的 `spawnSync`
 *   只要带**管道 stdio** 就返回 EBUSY —— 实测 `stdio: 'ignore'` / `'inherit'` 都正常 (status=0),
 *   `'pipe'` / 默认必 EBUSY; 且与可执行文件无关 (连 `process.execPath` 即 node.exe 自己都一样),
 *   也**不是**文件句柄/杀软占用 (重试 5 次 + 延迟全 EBUSY, 是确定性的, 不是竞态)。
 *   Playwright 把这一步 try/catch 静默吞掉 => 桩服务没死 => 子进程的 stdio 管道关不掉 =>
 *   `'close'` 不触发 => `waitForCleanup` 永不 resolve => **用例全 PASS 但命令永不退出、8137 残留**。
 *
 * 修法: 赶在 Playwright 自己的 plugin teardown 之前, 用**异步** `exec`(走 spawn, 不受该限制)
 *   把监听 8137 的进程树杀掉。顺序由 Playwright 的 task runner 保证: 全局 teardown 任务注册在
 *   plugin setup **之后**, 而 teardown 按注册的**逆序**执行 => 本函数先于 webServer plugin 的
 *   teardown; 等轮到它 `killProcess()` 时 `processClosed` 已为 true, 整段 force-kill 被跳过。
 *   (见 playwright/lib/runner/index.js 的 `createGlobalSetupTasks` / `runDeferCleanup`)
 *
 * 实测效果: 杀掉监听 PID 后 0.9s 内子进程 `'close'` 触发、端口释放 —— 也就是**不必**换成
 * 真实终端才能跑; 真实终端下本函数同样安全 (只是把 Playwright 自己那次 taskkill 提前做了)。
 *
 * 非 Windows 直接 no-op: POSIX 上 Playwright 走 `process.kill(-pid, SIGKILL)` 杀整个进程组,
 * 本来就没有这个问题 (CI 是 ubuntu-latest, 这条 no-op 必须保持)。
 */
import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import { PORT } from './harness.mjs';

const execAsync = promisify(exec);

/** netstat 的 PID 列 —— 本机 netstat 表头是中文, 但状态列恒为英文 `LISTENING`, 按状态词匹配即可。 */
const LISTENING_RE = new RegExp(`:${PORT}\\s+\\S+\\s+LISTENING\\s+(\\d+)`, 'g');

async function listeningPids() {
  const { stdout } = await execAsync('netstat -ano', { windowsHide: true, timeout: 15_000 });
  return [...new Set([...stdout.matchAll(LISTENING_RE)].map((m) => m[1]))];
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default async function globalTeardown() {
  if (process.platform !== 'win32')
    return;

  let pids = [];
  try {
    pids = await listeningPids();
  } catch (error) {
    console.warn(`[e2e] 收尾兜底: netstat 失败, 跳过 (${error.message})`);
    return;
  }
  /* 桩服务已自行退出 (或本就没起来) —— 无事可做。注意: webServer 起不来时 Playwright 会中断任务链,
   * 本函数根本不会被调用, 所以这里不会误杀别的 clone 占着 8137 的残留服务。 */
  if (!pids.length)
    return;

  console.log(`[e2e] 收尾兜底: 强制结束监听 ${PORT} 的进程树 (${pids.join(', ')})`);
  for (const pid of pids) {
    if (!/^\d+$/.test(pid))
      continue;
    try {
      await execAsync(`taskkill /PID ${pid} /T /F`, { windowsHide: true, timeout: 15_000 });
    } catch (error) {
      console.warn(`[e2e] 收尾兜底: taskkill ${pid} 失败 (${error.message})`);
    }
  }

  /* 等端口真正释放 —— 既给 Playwright 的 'close' 事件留出到达时间, 也让"杀对了对象"这件事自证。 */
  const deadline = Date.now() + 10_000;
  while (Date.now() < deadline) {
    await sleep(200);
    if ((await listeningPids().catch(() => [])).length === 0)
      return;
  }
  console.warn(`[e2e] 收尾兜底: 10s 内 ${PORT} 仍被监听 —— 可能有残留, 查 netstat -ano | findstr ${PORT}`);
}
