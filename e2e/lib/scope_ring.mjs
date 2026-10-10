// @ts-check
/**
 * 作用域审计环辅助(计划 26-10-10-2001 S5, 第三张网「运行时审计」的消费端)。
 *
 * 审计单点在 shared/scope_audit.js(_auditScope), 三个统一出口各记账一次; 本文件只负责:
 *   ① 打开审计开关 + 清环(e2e 专用, 生产默认关 —— T6 守阵钉住源码无赋值点, 打开只允许
 *      发生在这里, 即计划 §5b「e2e 用 Playwright 的注入脚本打开」的原话);
 *   ② 读环(审计环是页面内埋点, 没有 DOM 之外的取径 —— D4 第②类);
 *   ③ 断言环内无偏差记录(每条交互场景的收口断言: 下发载荷对 ≠ 还要"说谎为零");
 *   ④ S4 红验: 注入造一次不一致 -> 环里必须出现记录(守阵「审计真的会记账」的自证)。
 *
 * D4 断言翻译守则(e2e/lib/vm.mjs 头注)合规性: 开关赋值/清环/造不一致属第①类(注入/复原
 * 桩态), 读环属第②类(内部埋点)。除此之外本文件不做任何页面状态改动。
 */
import { expect } from '@playwright/test';

/**
 * 打开审计开关并清空环(每条用例 arrange 步调用, 在触发动作**之前**)。
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<void>}
 */
export async function armScopeAudit(page) {
  await page.evaluate(`(() => {
    window.__AQB_AUDIT_SCOPE__ = true;
    window.__AQB_SCOPE_RING__ = [];
  })()`);
}

/**
 * 读审计环全量记录(供失败消息带现场; 断言用 expectScopeRingClean)。
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<Array<{t:number, event:string, kind:string, keys:string[], hashes:string[], msg:string, sig:string}>>}
 */
export async function readScopeRing(page) {
  return page.evaluate(`window.__AQB_SCOPE_RING__ || []`);
}

/**
 * 收口断言: 环内不得有偏差记录(kind !== 'ok')。
 * 「下发载荷比对正确」只证明这一次走对了; 环干净证明出口层**没有**任何形状/去重/空载荷异常
 * —— 两层合起来才是「选中与触发一致」的完整实证(计划 §5.4 断言三层之二)。
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<void>}
 */
export async function expectScopeRingClean(page) {
  const ring = await readScopeRing(page);
  const bad = ring.filter((/** @type {{kind: string}} */ r) => r.kind !== 'ok');
  expect(bad, `审计环内不得有偏差记录(现场 ${JSON.stringify(ring).slice(0, 400)})`).toEqual([]);
}

/**
 * S4 红验注入: 在页面里**故意**造一次不一致(重复目标载荷)调 _auditScope, 返回环内 dup 记录。
 * 走真实出口方法(第①类注入桩态调用) —— 若审计被删/关/改坏, 这里拿不到 dup 记录即红。
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<{dupN: number, warned: boolean}>}
 */
export async function injectScopeDeviation(page) {
  return page.evaluate(`(() => {
    const vm = document.querySelector('#app')._vnode.component.proxy;
    const before = (window.__AQB_SCOPE_RING__ || []).length;
    // 重复目标 = M4 违例形态: 同一 hash 走两次通道
    vm._auditScope('red-probe', { keys: [], hashes: ['h-red', 'h-red'] });
    const ring = window.__AQB_SCOPE_RING__ || [];
    const dups = ring.slice(before).filter((r) => r.kind === 'dup');
    return { dupN: dups.length, warned: !!(dups[0] && dups[0].warned) };
  })()`);
}
