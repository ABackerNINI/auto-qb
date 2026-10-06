// @ts-check
import { defineConfig, devices } from '@playwright/test';
import { BASE_URL, HARNESS_CMD, READY_URL } from './e2e/harness.mjs';

/**
 * WEB UI 真浏览器冒烟 —— 本仓库"静态守阵之外"的那一层门禁。
 *
 * 定位(S7 终态, 2026-10-06): 旧单页冒烟脚本已退役, 本文件 + e2e/ 是 WEB UI 浏览器断言的
 * **全量单点** —— 全部 ≈105 处断言由 e2e/ 下按块拆分的 spec 承接(各文件头有对账映射表)。
 *   · 模式矩阵(双皮肤 × ok|error|hang × skip-check on|off × hr-scene on|empty|off)走 env
 *     参数化(见 e2e/harness.mjs); 「每次改前端」门禁 = `npm run test:e2e:fast`(@fast 子集,
 *     分钟级), 全量矩阵轮在收尾/排障时跑(六行命令见 .commands/dev/config.toml 的 dev.e2e note);
 *   · 桩服务由本配置的 webServer 自动拉起, 不需要人工先起 `scripts/ui_harness.py`。
 *
 * 为什么是 `.mjs` 而不是 `.js`: 根 `package.json` 是 `"type": "commonjs"`(不能改成 module ——
 * tests/test_extension_proxy.py 会对 extensions 下的 .js 跑 `node --check`, 改 type 会让它们被按
 * ESM 解析)。仓库既有约定就是**显式扩展名**: ESM 用 `.mjs`、确需 CJS 的脚本用 `.cjs`, 同一原因。
 */
export default defineConfig({
  testDir: './e2e',

  /* Windows 上给 webServer 收尾兜底 —— 不兜的话用例全 PASS 但命令永不退出(根因与实测见该文件
   * 顶部注释)。非 Windows 是 no-op, CI 不受影响。 */
  globalTeardown: './e2e/global-teardown.mjs',

  /* 桩服务是**单个共享实例**, 用例之间会互相影响观测(轮询 / 乐观态), 故不并发 ——
   * 这是冒烟不是压测, 确定性优先于速度。 */
  fullyParallel: false,
  workers: 1,

  /* 源码里留了 test.only 就别让 CI 静默少跑 */
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,

  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: BASE_URL,
    /* 失败重跑时留 trace —— 时序类故障(乐观 UI 回滚 / 合帧竞态)光看断言消息看不出时序 */
    trace: 'on-first-retry',
  },

  /* 只配 chromium: 本项目 UI 是内部工具, scaffold 默认的 firefox+webkit 三浏览器矩阵纯属浪费。
   * 视口 1440x900 沿用旧冒烟轨的既定口径 —— 行窗口化 / 版式类断言对宽度敏感, 改了会得出不同结论。 */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],

  webServer: {
    command: HARNESS_CMD,
    url: READY_URL,
    /* ❗**不复用**已存在的服务: 多 clone 工作区下复用会连上别的 clone 的残留 harness,
     * 于是"全 PASS"验的是旧代码(smoke.md 记的假信心事故)。端口被占时宁可直接失败。 */
    reuseExistingServer: false,
    timeout: 120_000,
    /* 把桩服务首行(监听地址 + 种子/组数)打进日志 —— 排障第一眼看的就是它 */
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
