# 4327 passed + 2 skipped —— reannounce 确认跟踪消解等待模型落地(issue 26-10-31-1740)

> 摘要: reannounce 确认跟踪消解等待模型落地(issue 26-10-31-1740)
> 基线时间: 2026-11-01 00:25
**Refs:** memory-bank/tasks/26-10-31-webui-write-side.md

## 验收数字

`commands run test.full` 实测(2026-11-01 00:22, commit 待提交态):

```
TOTAL                                                21805    145   7394    122    99%
4327 passed, 2 skipped in 161.51s (0:02:41)
```

- 通过数与上一基线同数(4327 passed + 2 skipped); skipped 仍为 tests-real 真机轨(不在 testpaths)与平台态 skip。
- 真机面(独立轨, 不进本数字): `commands run real.run -- --case RM09-04 --yes` 1 passed(41.47s); `commands run real.suite -- --slice RM09 --yes` 10 passed(81.17s)。

## 本改动面

- `src/auto_qb/webui/commands.py`: `_verdict_reannounce` 消解等待模型重写(②在途直证全域废除; ④' 拒绝域扩 {4,5,6}+msg; 新③″ working 转换正证据) + docstring/常量组注释同步; 判定函数纯函数形状不变。
- `src/auto_qb/webui/runtime.py`: 超时 warn 尾巴去「在途」改「working 转换/epoch 前跳/拒绝证据」; check_pending docstring 对齐新判定表。
- `tests/test_web_commands.py`: 三个判定矩阵测试按新语义重写(epoch/legacy/min_window; 语义变更重写非弱化, docstring 记 D2 依据) + 文件头测试计划同步。
- `tests-real/rm09_webui_write/test_rm09_webui_write.py`: RM09-04 ③ 改道伪 tracker 场景(ok 回执 + 窗内推迟两态), 聚合回执前缀断言改咬 truth.results; RM09 整片回归 10/10。
- `tests-real/lib/tracker.py`: FakeTracker 响应显式回传 `min_interval`(= interval), 使 min_announce 时序确定。
- 用例数不变(重写非新增): 4327 与上基线同。
