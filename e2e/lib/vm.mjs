// @ts-check
/**
 * Vue 根实例探针封装 —— 从页面拿 Vue vm 的唯一直径(e2e 全部 spec 复用)。
 *
 * 判据锚 memory-bank/pitfalls/testing/smoke.md「Vue 3.5.13 取根实例」条:
 *   · `#app.__vue_app__._instance` **恒为 null**(键在但没值) —— 别改回去, 踩过一次;
 *   · 只能走 `document.querySelector('#app')._vnode.component.proxy`;
 *   · 无头页里 Vue 实例**不在 window 上**(模块作用域), 只能经 evaluate 操作。
 *
 * D4 断言翻译守则(计划 26-10-06-0708 §3.5, 本 lib 四件统一遵守):
 *   · evaluate 只允许两类: ①注入/复原桩态 ②vm 内部时序探针 —— 本文件的读数属第②类
 *     (vm 埋点/内部字段没有 DOM 之外的取径); 凡有真实 UI 路径的交互一律 locator 手势, 不得借道 vm;
 *   · 修饰键/行点击落点纪律: 行左缘 position:{x:8,y:8} 避开 .site-chip 等交互后代;
 *   · 阈值数字(P1-2/P1-3 预算、2500~6000ms 窗口、轮询分档期望值)逐字保留。
 */

/**
 * 页面内取 Vue 根实例的表达式片段(供拼进 evaluate 字符串)。
 * @type {string}
 */
export const INST = "document.querySelector('#app')._vnode.component.proxy";

/**
 * 在页面里求一个 vm 表达式(取不到 vm 返回 null, 调用方自行降级/断言)。
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} expr —— 页面内可求值的表达式, `vm` 已绑定根实例, 如 `"vm.renderMs"`。
 * @returns {Promise<*>} 表达式求值结果; vm 不存在时为 null。
 */
export async function readInst(page, expr) {
  return page.evaluate(`(() => { const vm = ${INST}; return vm ? (${expr}) : null; })()`);
}

/**
 * 在页面里执行一段以 vm 为前提的语句块(注入/复原桩态用 —— D4 允许的第①类 evaluate)。
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} body —— 页面内执行的语句, `vm` 已绑定根实例, 如 `"vm.hrsHist.badOnly = false;"`。
 * @returns {Promise<*>} 语句块返回值(body 末尾带 return 才有)。
 */
export async function withVm(page, body) {
  return page.evaluate(`(() => { const vm = ${INST}; ${body} })()`);
}
