// @ts-check
/**
 * 运行时错误采集 + 「无 console.error / pageerror」公共检查 —— 断言单点(e2e 全部 spec 复用)。
 *
 * Dark Reader 这类**企业策略强装**的扩展即使 `--disable-extensions` + 全新 profile 也会注入并报错
 * (memory-bank/pitfalls/testing/smoke.md), 故按来源过滤 chrome-extension —— 否则本断言在本机会恒红。
 *
 * D4 断言翻译守则(计划 26-10-06-0708 §3.5, 本 lib 四件统一遵守, 迁移各批照此评审):
 *   · evaluate 只允许两类: ①注入/复原桩态 ②vm 内部时序探针; 其余交互一律真实手势(getByRole 优先), 保留处必须注释理由;
 *   · 修饰键/行点击落点纪律: 行左缘 position:{x:8,y:8} 避开 .site-chip 等交互后代(smoke.md);
 *   · 阈值数字(P1-2/P1-3 预算、2500~6000ms 窗口、轮询分档期望值)逐字保留 —— 它们是回归基准, 不是实现细节。
 */
import { expect } from '@playwright/test';

/**
 * 采集本页的运行时错误。必须在测试一开始(page 还没 goto)就调 —— 挂的是事件监听, goto 后挂会漏。
 * 登记进内部 WeakMap, 供 installRuntimeErrorGuard 的 afterEach 读取。
 *
 * @param {import('@playwright/test').Page} page —— 必须显式标注: 仓库开了 `// @ts-check` 且没有
 *   tsconfig/jsconfig, TS 走默认严格档, 裸写 `page` 就是 ts(7006) 隐式 any。
 * @returns {string[]} 错误文本列表(空数组 = 本页无运行期错误)。
 */
const errorStore = new WeakMap();

export function collectRuntimeErrors(page) {
  /** @type {string[]} —— 不标注会被当成"演化中的 any[]"(ts(7005)), 与上面的 7006 成对出现。 */
  const errors = [];
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    if ((m.location()?.url || '').startsWith('chrome-extension://')) return;
    const text = m.text();
    if (text.includes('chrome-extension://')) return;
    errors.push(`console.error: ${text}`);
  });
  errorStore.set(page, errors);
  return errors;
}

/**
 * afterEach 公共检查: 「无 console.error / pageerror」(旧单页冒烟脚本收尾总检的框架化,
 * 语义更强 —— 从"整轮最后一眼"变成"每条 test 各自把关")。在 describe/文件顶层调一次:
 *
 *   installRuntimeErrorGuard(test);   // 组内每条 test 结束时自动断言本页零运行期错误
 *
 * 注意: 组内仍可在测试体内提前断言 collectRuntimeErrors 的返回值(如"跨过一个轮询周期再看错误"
 * 的口径, 那是断言语义本身, 见 smoke.spec.mjs) —— 两处断言同一数据源, 不算两处定义。
 *
 * @param {import('@playwright/test').Test} test —— 由调用方传入(本文件不 import 默认 test,
 *   同一个 lib 要同时服务于普通 describe 与 serial 组)。
 */
export function installRuntimeErrorGuard(test) {
  test.afterEach(async ({ page }) => {
    const errors = errorStore.get(page) ?? [];
    expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
  });
}
