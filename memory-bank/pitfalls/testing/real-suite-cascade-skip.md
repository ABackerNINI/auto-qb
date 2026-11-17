# real.suite 级联 skip: 一条失败拖垮整模块

> 摘要: 真机 suite 一条用例失败后的收尾恢复只等 WEB 可达, libtorrent connect 滞后窗内**按字母序下一个模块**的模块闸 `check_online` 单发探测撞窗 → 整模块成块 SKIP —— **跨文件级联**的环境级假红形态; skip 必须单跑核真实三态, 不能当 BLOCKED 记账。
> 触发: 真机 suite, 级联 skip, 整模块 skip, check_online, qb_up, libtorrent 滞后窗, 环境级假红, RM04 级联, suite skip 成块
**Added:** 2026-11-17 08:44 (片A 实测发现, 切片 26-11-17-0756-real-rm04-sliceA)
**Refs:** memory-bank/testing/real-machine.md §2.4, memory-bank/testing/real-baselines/26-11-17-0756-real-rm04-sliceA.md

## 事故形态

`real.suite --slice RM04 --yes` 一轮 97s: 9 FAIL / 1 PASS / **11 SKIP**。11 条 skip 不是用例自身跳过 —— RM04-21(在 reconcile_reenter.py, 与被 skip 的 11 条**不同文件**)失败后, 其 finally 的 `qb_up` 只等 WEB 起来, 此时 libtorrent 尚处 connect 滞后窗; **按字母序的下一个模块**(relocate.py)的模块级环境闸 `check_online` **单发**探测撞进该窗判定不可用 → 整个模块(11 条)按环境不可用 skip —— **跨文件级联**, 殃及的不是失败用例本模块。suite 日志里表现为整模块成块 skip, 极易误读成「这些用例环境性不可跑」。

## 根因

- 失败用例的收尾恢复(qb_up)成功判据太宽(WEB 端口可达 ≠ libtorrent session connected), 与 §2.4 的 `connection_status=disconnected` 陷阱同根。
- 模块闸探测单发、无重试窗, 一次撞上滞后窗就把整模块判死。

## 坑传递要点

- 跑完 suite 先看 **skip 数**: skip 集中成块(整模块)= 级联嫌疑, 必须**单跑核真实三态**, 不能把 suite 的 skip 当 BLOCKED 记账(片A 实测: suite 11 skip, 单跑补跑后 11 条里 9 条真实 FAIL + 2 条 PASS(RM04-04/07), 两轮取证三态一致, 与切片 26-11-17-0756 §04.3 对账)。
- 修用例收尾/造数时, `qb_up` 后要等 libtorrent 真连接(参照 §2.4 只接受 connected/firewalled), 不以 WEB 可达为充分条件; 模块闸探测带重试窗(待改造面, 涉 conftest 通用基建, 修时入批)。
