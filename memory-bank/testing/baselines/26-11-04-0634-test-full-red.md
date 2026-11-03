# 5134 passed, 10 skipped(根) —— spy Thread.start 量法替换全局 active_count 快照(issue 26-11-04-0600 test 修复后)

> 摘要: spy Thread.start 量法替换全局 active_count 快照(issue 26-11-04-0600 test 修复后)
> 基线时间: 2026-11-04 06:34
**Refs:** memory-bank/issues/26-11-04-0600-test-testing-persist-thread-active-count.html

## 验收数字

`commands run test.full`(2026-11-04 06:20 起跑, 198.3s):

```
TOTAL                                                23937    228   8184    170    99%
  5134 passed, 10 skipped in 195.00s (0:03:14)
```

口径注记:
- 本基线验证 issue 26-11-04-0600 的修复: `test_all_persist_writes_on_caller_thread` 的全局
  `threading.active_count()` 快照断言改为 spy `threading.Thread.start`(窗口内未启动线程),
  量法对同 xdist worker 无关线程启停免疫。
- 红验: 向 `on_task_line` 临时注入 `Thread(...).start()` 突变, 单跑判红(报 `模块新建了线程:
  ['mutation-probe']`), 还原后转绿; `src/` 已零 diff。
- 修复前同日 06:05 预修复全量亦绿(5134 passed, 271.74s) —— 偶发问题单次复验跑绿不作「已消失」结论。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_traffic_store_codec.py` | `test_all_persist_writes_on_caller_thread`: 删 `threads_before` 全局快照断言, 改 monkeypatch `threading.Thread.start` 记录窗口内启动的线程名并断言为空 |

未改生产代码(`src/` 零 diff, 红验突变已还原); 用例语义不变(仍是「落盘在调用线程 + 模块不建线程」)。
