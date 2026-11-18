# e2e 多整页 reload 用例撞 Playwright 默认 30s test 超时(容器慢速下被误读成"挂死/超时不可见")

> 摘要: playwright.config.mjs 未设 test 级 `timeout`, 每个用例默认 30s。单用例含**两次及以上整页 reload** 的重用例(round-trip 形态: 导出三轮/导入两轮 + 双 reload)在 Windows ~19s, 在容器(软件渲染 + 串行拉模板/脚本 ~48ms/请求, 整条 boot ~5s)实测 >30s —— 死在最后一次 reload 后的 visibility 等待, 表象(「reload 后等整组迁移块 30s 超时」「element(s) not found」)极易误读成"服务端挂死/迁移没触发/位置持久化坏了", 实际是纯时间预算耗尽, boot 还在正常推进。
> 触发: e2e 容器红, reload 后 toBeVisible 超时, element(s) not found, 30s 超时, Test timeout of 30000ms exceeded, round-trip, settings-backup, 整组迁移, 服务端挂死误判

## 本篇只回答

容器 e2e 用例在「reload 后等元素不可见」上确定性红时的判别: 是挂死还是时间预算耗尽, 以及取证与修法的单点。reload 位置持久化的产品行为、route 收尾竞态(坑档 route-callback-teardown-race)不在此篇。

### 判别: 预算耗尽 vs 挂死, 看三个证据面 (2026-11-19 issue 26-11-19-0230 取证实录)

- **触发**: settings-backup round-trip 用例容器内双皮肤确定性红, 红点 = 还原导入后 reload 等「整组迁移」input 30s 不可见; 三层对照实验(单独跑/暂存改动跑/连跑)都红, 更加深"环境既有失败"的错觉。
- **判别**(按序做, 三个证据面任一命中即预算问题): ① 失败后**同桩后续用例是否全过** —— 挂死会拖死共享桩的后续用例, 预算耗尽不影响(本次失败后 10 例全绿); ② **trace 末尾网络时间线**(`--trace on` 透传见 commands-e2e-arg-passthrough-three-dashes)—— 预算耗尽的形态是 teardown 时刻请求仍在 200 串行推进(本次 `columns_grid.js` st=-1 只是"被 teardown 截断的最后一个", 前面 ~15 个请求每 ~48ms 一个稳定 200), 挂死的形态是某时刻后全部请求停摆; ③ 算**测试级预算账**: trace 时间戳上"最后一次 reload 的点击"到"test 起跑"的差 + reload 后 boot 实际耗时 vs 30s —— 本次点击在 test 第 27.3s, boot 还需 ~3-5s, 预算只剩 2.7s。
- **处置**: 用例首行 `test.setTimeout(90_000)` + 注释写明实测数字(先例: column-prefs.spec.mjs:146 双整页加载 90s)。不要去修"等待条件"或"迁移触发链"——先验根因再动刀, 本例等待条件本身没有问题。
- **复发**: 0

**Refs:** memory-bank/issues/26-11-19-0230-test-e2e-settings-backup-container-fail.html
