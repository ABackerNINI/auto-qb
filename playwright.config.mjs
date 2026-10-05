// @ts-check
import { defineConfig, devices } from '@playwright/test';
import { BASE_URL, HARNESS_CMD, READY_URL } from './e2e/harness.mjs';

/**
 * WEB UI 真浏览器冒烟 —— 本仓库"静态守阵之外"的那一层门禁。
 *
 * 定位(2026-10-06 定, 方案 A):
 *   · 本文件 + e2e/ 只跑"每次改前端都该过一遍"的最小集(渲染健康 + 数据契约), 目标是**快**;
 *   · 人工深挖(105 项断言 / 双皮肤 × ok|error|hang 三模式)仍走 `scripts/ui_smoke.cjs`,
 *     那条链路的完整环境坑见 memory-bank/pitfalls/testing/smoke.md;
 *   · 桩服务由本配置的 webServer 自动拉起, 不需要人工先起 `scripts/ui_harness.py`。
 *
 * 为什么是 `.mjs` 而不是 `.js`: 根 `package.json` 是 `"type": "commonjs"`(不能改成 module ——
 * tests/test_extension_proxy.py 会对 extensions 下的 .js 跑 `node --check`, 改 type 会让它们被按
 * ESM 解析)。仓库既有约定就是**显式扩展名**: `scripts/ui_smoke.cjs` 用 `.cjs` 正是同一原因。
 */
export default defineConfig({
  testDir: './e2e',

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
   * 视口对齐 ui_smoke.cjs 的 1440x900 —— 行窗口化 / 版式类断言对宽度敏感, 两处不一致会得出不同结论。 */
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
