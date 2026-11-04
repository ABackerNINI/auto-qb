# 5339 passed, 10 skipped —— 测试伪断言批量修复(16 处)后全量基线

> 摘要: 测试伪断言批量修复(16 处)后全量基线
> 基线时间: 2026-11-05 04:15
**Refs:** memory-bank/issues/26-11-05-0344-test-qbmanager-tasks-missing-assert.html

## 验收数字

`commands run test.full` 实测(2026-11-05 04:15, Windows, 本机):

- 汇总行: `5339 passed, 10 skipped, 1 warning in 155.53s (0:02:35)` —— 0 failed
- 覆盖率 TOTAL 表末行: `TOTAL 24463 69 8390 38 99%`(语句 24463 / 缺 69 / 分支 8390 / 部分覆盖 38)
- 口径注记: 全量阈值判定通过(退出码 0); 副作用台账越界 0。与上基线(26-11-05-0253)逐位一致(本轮纯测试文件内断言形态改写, 测试数与覆盖面不变)。

## 本改动面

- `tests/test_qbmanager_tasks.py` 等 7 个测试文件: 修复 16 处缺 `assert` 前缀的元组表达式伪断言(校验实际仍生效, 丢失的只是失败消息), 三型改法:
  - `assert_not_called(), "msg"` → `assert not X.call_args_list, "msg"`(4 处)
  - `assert_called_once(), "msg"` → `assert X.call_count == 1, "msg"`(3 处; 首版误改 `call_args_list == [mock.call()]` 被 test_web_views_reload 实测红逮住, 原契约只数次数不管实参)
  - `assert_called_once_with(...), "msg"` → `assert X.call_args_list == [mock.call(...)], "msg"`(9 处, 含 issue 26-11-05-0344 本件 2 处)
- `memory-bank/`: issue 26-11-05-0344 翻 Done(复验/实际修法改道原因/扩展扫描留痕), 索引重建
