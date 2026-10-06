// @ts-check
/**
 * 乐观态时序探针(armPending / armClick / readPending) —— 从 scripts/ui_smoke.cjs L83–117
 * **照搬移植**(计划 26-10-06-0708 §3.4 D3), 包装成 page 级 install/read 两段式:
 *   ① install: 点击前 `armPending(page, sel?)` 装记录器(+ 可选 `armClick(page, handle)` 定时刻基准)
 *   ② act:     真实手势触发(Playwright click / 右键)
 *   ③ read:    事后 `readPending(page)` 问"它**曾经**出现过吗 / 什么时候消失的"
 *
 * 为什么必须"记录器"而不是"事后再数 .is-pending"(照搬 ui_smoke.cjs 原注释, 2026-09-19 定):
 * 真值对齐修好之前, pending 要挂满 3s 兜底 ⇒ "等 120ms 再数一次 .is-pending"这种采样稳过;
 * 修好之后 pending 只活 100~300ms, 事后再采样恒为 0 ⇒ 那些断言会**集体恒红**(不是回归, 是度量方式失效)。
 *
 * D4 断言翻译守则(计划 26-10-06-0708 §3.5, 本 lib 四件统一遵守):
 *   · evaluate 只允许两类: ①注入/复原桩态 ②vm 内部时序探针 —— 本文件属第②类(MutationObserver +
 *     10ms 采样在页面内跑, Node 侧装不上; 时序窗口 2500~6000ms 是断言语义, 原样保留);
 *   · 修饰键/行点击落点纪律: 行左缘 position:{x:8,y:8} 避开 .site-chip 等交互后代;
 *   · 阈值数字逐字保留(含本文件 readPending 消费侧的窗口判据, 由使用批自带)。
 */
import { INST } from './vm.mjs';

/**
 * 安装 pending 生灭记录器(点击前调)。默认盯 `.is-pending`, 可换选择器。
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} [sel='.is-pending']
 * @returns {Promise<void>}
 */
export async function armPending(page, sel = '.is-pending') {
  await page.evaluate(`(() => {
    const vm = ${INST};
    const SEL = ${JSON.stringify(sel)};
    window.__p = { t0: null, appear: null, gone: null, peak: 0, peakT: null, sel: SEL };
    const bump = () => {
      const p = window.__p;
      const n = Object.keys(vm.pendingOps || {}).length;
      if (n > p.peak) { p.peak = n; p.peakT = p.t0 ? Math.round(performance.now() - p.t0) : null; }
    };
    if (window.__pmo) window.__pmo.disconnect();
    window.__pmo = new MutationObserver(() => {
      const p = window.__p;
      const has = !!document.querySelector(p.sel);
      if (p.appear === null && has) p.appear = performance.now();
      if (p.appear !== null && p.gone === null && !has) p.gone = performance.now();
      bump();
    });
    window.__pmo.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"], childList: true });
    clearInterval(window.__ptimer);
    window.__ptimer = setInterval(bump, 10);
  })()`);
}

/**
 * 把时刻基准(t0)钉在菜单项的 click 事件上(捕获阶段) —— 不用 Playwright 的 click 时刻
 * (含鼠标移动开销), 时序数字才是纯前端侧的。在触发点击**之前**对目标元素调。
 *
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').ElementHandle} handle —— 目标元素(如 .ctx-item 的 handle)。
 * @returns {Promise<void>}
 */
export async function armClick(page, handle) {
  await handle.evaluate((el) => el.addEventListener('click', () => { window.__p.t0 = performance.now(); }, { capture: true, once: true }));
}

/**
 * 读取记录器结果(事后调, 相对 t0 的 ms 数; t0 未钉时各时刻为 null)。
 *
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<{appear: number|null, gone: number|null, peak: number, peakT: number|null}>}
 *   appear/gone: pending 出现/消失相对 t0 的 ms; peak: pendingOps 并发峰值; peakT: 峰值出现时刻。
 */
export async function readPending(page) {
  return page.evaluate(`(() => {
    clearInterval(window.__ptimer);
    const p = window.__p;
    const r = (x) => ((p.t0 && x) ? Math.round(x - p.t0) : null);
    return { appear: r(p.appear), gone: r(p.gone), peak: p.peak, peakT: p.peakT };
  })()`);
}
