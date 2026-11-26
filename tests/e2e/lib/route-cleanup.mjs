// @ts-check
/**
 * e2e 收尾竞态兜底: 用例结束时 page.route 回调仍在飞行 → "Test ended" 假红 —— 单点兜底。
 *
 * 机制(issue 26-11-13-0234, env3 全量轮 2/344 红实证): 桩回调体内含 await(route.fetch 等)
 * 时, 回调是异步飞行物 —— 用例末段触发的那次请求, 其回调与用例收尾(page fixture 关闭)
 * 竞速, 输家的 route.fetch 在 test ended 之后才完成, playwright 把回调错误记成用例失败。
 * 断言本体全绿, 纯收尾假红; 本机 retries=0 直接红, CI retries=1 靠重试掩盖(探测器口径,
 * retry 不是修复, 见 flaky-ledger.md)。
 *
 * 用法(与 installRuntimeErrorGuard 同款, 传 test 注册 file 级 afterEach):
 *   import { installRouteCleanup } from './lib/route-cleanup.mjs';
 *   installRouteCleanup(test);   // 文件顶层调一次, 本文件全部用例收尾时卸载全部路由
 *
 * 语义: behavior:'ignoreErrors' = 不等飞行中的回调完成、其后续抛错一并忽略 —— 只消收尾
 * 竞态, 不吞用例运行期内的真实路由错误(运行期错误照常红)。差分证据 = 修复轮复验
 * (修前单跑 6 例 2 红 ↔ 修后全绿) + 静态接线守阵(tests/test_flaky_timing_guards.py
 * 扫描器 5, 摘接线必红); 运行期差分守阵经实证不可构造(归账三形态, 见坑档)。
 *
 * 什么时候装: 桩回调体内有 await(真实网络 route.fetch / 人为延时)的 spec 一律装;
 * 纯同步 route.fulfill 回调的窗口与单次协议往返同阶, 未实证到假红可暂不装
 * (机制面与判据: memory-bank/pitfalls/testing/route-callback-teardown-race.md)。
 */

/**
 * 注册 file 级 afterEach: 每条用例结束时卸载该 page 的全部 route, 并忽略仍在飞行的
 * 回调后续抛出的错误(含 "Test ended")。
 *
 * @param {import('@playwright/test').Test} test —— 由调用方传入(本文件不 import 默认 test,
 *   同一个 lib 要同时服务于普通 describe 与 serial 组, 与 errors.mjs 同款)。
 */
export function installRouteCleanup(test) {
  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });
}
