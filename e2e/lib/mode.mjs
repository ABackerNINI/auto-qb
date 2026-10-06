// @ts-check
/**
 * 模式矩阵门控 helper —— env 参数化(harness.mjs)的测试侧消费口(计划 26-10-06-0708 §3.2 D1)。
 *
 * 用法(在 describe 回调顶层调一次, 模式不符则**整组** test.skip):
 *
 *   import { requireMode } from './lib/mode.mjs';
 *   test.describe('乐观 UI 回滚族', () => {
 *     requireMode(test, { cmdResult: 'error' });          // 单值
 *     requireMode(test, { cmdResult: ['error', 'hang'] }); // 多值任一即跑
 *     requireMode(test, { skipCheck: 'off', hrScene: 'on' });
 *     test('...', async ({ page }) => { ... });
 *   });
 *
 * 防静默少跑(计划 §6 R2): skip 消息**必须**带当前 env 值 —— 排障一眼看出"为什么没跑"。
 * 矩阵合法性自检在 harness.mjs 的 assertModesValid()(module load 即 fail fast), 本文件
 * import 时即再触发一次; 四个当前值也从这里转出, spec 别直接读 process.env(那会绕开单点)。
 *
 * D4 断言翻译守则(计划 26-10-06-0708 §3.5, 本 lib 四件统一遵守):
 *   · evaluate 只允许两类: ①注入/复原桩态 ②vm 内部时序探针; 保留处必须注释理由;
 *   · 修饰键/行点击落点纪律: 行左缘 position:{x:8,y:8} 避开 .site-chip 等交互后代;
 *   · 阈值数字(P1-2/P1-3 预算、2500~6000ms 窗口、轮询分档期望值)逐字保留。
 */
import {
  CMD_RESULT,
  HR_SCENE,
  SKIP_CHECK,
  TORRENTS,
  assertModesValid,
} from '../harness.mjs';

/** module load 即自检 —— env 写错在本批任何 spec 加载瞬间就炸, 不等到 webServer 起。 */
assertModesValid();

/** 当前模式四元组(与 ui_harness.py 桩形态同源, 桩与断言不会漂)。 */
export { CMD_RESULT, SKIP_CHECK, HR_SCENE, TORRENTS };

/** env 键的可读标签(skip 消息里直接引用, 排障照着抄就能改 env)。 */
const ENV_KEYS = {
  cmdResult: 'E2E_CMD_RESULT',
  skipCheck: 'E2E_SKIP_CHECK',
  hrScene: 'E2E_HR_SCENE',
  torrents: 'E2E_TORRENTS',
};

/** 当前值对照表(requireMode 的比较与 skip 消息共用同一来源)。 */
const CURRENT = {
  cmdResult: CMD_RESULT,
  skipCheck: SKIP_CHECK,
  hrScene: HR_SCENE,
  torrents: TORRENTS,
};

const asList = (v) => (Array.isArray(v) ? v : [v]);

/** @type {readonly (keyof typeof CURRENT)[]} —— 不标注则 dim: string, req[dim] 会报 ts(7053)。 */
const DIMS = ['cmdResult', 'skipCheck', 'hrScene', 'torrents'];

/**
 * 模式门控: 任一维度不满足当前 env 就把整组 skip, 消息带当前值与要求值。
 *
 * @param {import('@playwright/test').Test} test —— 调用方传入的 test 对象(describe 回调内可用)。
 * @param {{cmdResult?: string|string[], skipCheck?: string|string[],
 *          hrScene?: string|string[], torrents?: number}} req —— 各维度要求(多值 = 任一即跑)。
 */
export function requireMode(test, req) {
  const reasons = [];
  for (const dim of DIMS) {
    const wanted = req[dim];
    if (wanted === undefined) continue;
    const allowed = asList(wanted);
    if (!allowed.includes(CURRENT[dim]))
      reasons.push(`当前 ${ENV_KEYS[dim]}=${CURRENT[dim]}, 本组要求 ${allowed.join('|')}`);
  }
  if (reasons.length)
    test.skip(true, `模式不匹配, 整组跳过 —— ${reasons.join('; ')}`);
}
