# e2e 桩回调内 await 是飞行物: 用例结束时 route 调用报 "Test ended" 假红

> 摘要: `page.route` 桩回调体内含 `await`(`route.fetch` 等)时, 回调是异步飞行物 —— 用例末段触发的
> 那次请求, 其回调与用例收尾(page fixture 关闭)竞速, 输家的 route 调用在 test ended 之后才完成,
> playwright 把回调错误归账成用例失败(`route.fetch: Test ended ... while running route callback`)。
> 断言本体全绿、error-context 快照各断言面正确, 纯收尾假红; 本机 `retries:0` 直接红,
> CI `retries:1` 被重试掩盖(探测器口径, retry 不是修复)。env3 全量轮 2/344 实证(issue 26-11-13-0234)。
> 触发: route.fetch, Test ended, 收尾竞态, teardown race, unrouteAll, ignoreErrors, installRouteCleanup,
> stubDisk, page.route 假红, route callback, 断言全绿仍红, 收尾假红

### 判别: 收尾竞态假红 vs 真失败

- **触发**: 桩回调内 `await route.fetch()`(真取上游响应再改写回放)的 spec + 用例末段恰有一次该类请求
  (app 对 `/api/config` 等的轮询/重拉面)。同文件所有共用桩的用例同险。
- **判别**: ①报错原文含 `Test ended` 且指回回调内的 `route.fetch`/`route.fulfill` 行, 自带官方建议
  `Consider awaiting page.unrouteAll({ behavior: 'ignoreErrors' })`; ②error-context 快照断言面全对
  (UI 无回归); ③同轮其余用例全绿, 单跑也可能复现(修前 clone2 单跑 6 例即 2/6 红, 不必等全量轮)。
- **机制(归账三形态, 2026-11-13 实测)**: 「**运行期内发起、结束后才完成**」的 route 调用会归账记红
  (issue 实证形态, 报错带完整 call log); 「**结束后才发起**」的(`sleep` 后再 fetch / fetch 后 `sleep`
  再 fulfill 两形态都试过)被 playwright **静默吞掉不归账**; in-flight 跨界窗 = 服务端往返毫秒级、
  由服务端控速 ⇒ **运行期差分守阵不可构造**(构造守阵三次尝试全不可靠, 别再试), 差分证据只能走
  修复轮复验: 修前红(真实复现) ↔ 修后绿。
- **处置**: `e2e/lib/route-cleanup.mjs` 的 `installRouteCleanup(test)`(file 级 afterEach
  `page.unrouteAll({ behavior: 'ignoreErrors' })`), 文件顶层调一次, 全文件用例受益; 桩回调体内含
  await 的 spec 一律装。`ignoreErrors` 只消收尾竞态, 不吞运行期内的真实路由错误(运行期错误照常红)。
  纯同步 `route.fulfill` 桩窗口与单次协议往返同阶, 未实证假红可暂不装(装了也无害)。
- **别踩的坑**: ①回调内 try/catch 吞 Test ended 类错 —— 能消红但掩盖真实路由错误, 不推荐; ②CI retry
  绿了就当修好 —— 违反台账纪律(retry 不是修复); ③想用运行期守阵钉差分 —— 见机制节, 物理不可行,
  差分锚在静态面(下条)。
- **守阵**: `tests/test_flaky_timing_guards.py` 扫描器 5(`test_repo_route_fetch_specs_wired_route_cleanup`):
  含 `route.fetch(` 调用位的 `*.spec.mjs` 必须在**文件顶层**接线 `installRouteCleanup`; 两侧取噪声方向
  相反的安全侧 —— 违例侧看原文按调用位判(注释提及也算, 先取后 await 的分离形态同拦), 接线侧**剥注释后
  判行首无缩进的调用形态**(import 单独在场不算接线, 只注释调用行 = 临时关闸照样红, describe 内缩进调用
  ≠ 顶层); 兜底单点本体另有静态钉(lib 剥注释后必须含 unrouteAll + ignoreErrors 字面); 活性探针钉
  「未接线/已接线/两行全注释/只注释调用行/describe 作用域调用/注释提及/分离 await/纯 fulfill 放行」八形态。
  扫描面边界: 只扫 `*.spec.mjs`, 桩助手收敛进 `e2e/lib/` 时须同步扩面。台账行见
  `memory-bank/testing/flaky-ledger.md`(2026-11-13)。

**Refs:** memory-bank/issues/26-11-13-0234-test-e2e-stubdisk-teardown-race.html · e2e/lib/route-cleanup.mjs
