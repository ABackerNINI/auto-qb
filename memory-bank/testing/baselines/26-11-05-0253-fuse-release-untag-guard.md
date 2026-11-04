# 5339 —— fuse release 摘标签 None-client 守卫修复后全量基线

> 摘要: fuse release 摘标签 None-client 守卫修复后全量基线
> 基线时间: 2026-11-05 02:53
**Refs:** memory-bank/issues/26-11-05-0200-bug-fuse-untag-none-client-guard.html

## 验收数字

`commands run test.full` 实测(2026-11-05 02:53, Windows, 本机):

- 汇总行: `5339 passed, 10 skipped, 1 warning in 148.45s (0:02:28)` —— 0 failed
- 覆盖率 TOTAL 表末行: `TOTAL 24463 69 8390 38 99%`(语句 24463 / 缺 69 / 分支 8390 / 部分覆盖 38)
- 口径注记: 定点子集跑(`-k` 过滤)出现的 `FAIL Required test coverage of 99.5% not reached` 属子集运行覆盖率必然不达阈值的预期现象, 非回归; 全量阈值判定通过(退出码 0)。变异验证:临时撤销摘标签守卫后新用例 `test_fuse_release_untag_skipped_when_client_none` 必红(AttributeError), 恢复后复绿。

## 本改动面

- `src/auto_qb/core/modules/fuse_mod.py`: `release()` 摘标签调用点补 `api is None or api.client is None` 守卫——降级为 WARNING「放行跳过摘标签(标签保留)」+ 跳过请求, 与写回侧同口径(26-11-05-0200)
- `tests/test_fuse_mod.py`: 新增 `test_fuse_release_untag_skipped_when_client_none` 直驱用例(真 trigger 流走到 triggered+标签在场后 `api.bind(None, store)` 断连再 release, 断言零 qB 请求/只标 released/标签保留/告警在场); 头部 docstring 测试计划清单同步补行
- `memory-bank/`: issue 26-11-05-0200 翻 Done(复验/实际修法/验证方式留痕)
