# 4883 passed + 2 skipped(根) —— sidefx 串行临时根假阳性修复(sidefx 延迟求值+签名缓存)后全量

> 摘要: sidefx 串行临时根假阳性修复(sidefx 延迟求值+签名缓存)后全量
> 基线时间: 2026-11-02 22:23
**Refs:** memory-bank/issues/26-11-02-2142-test-sidefx-serial-false-positive.html, memory-bank/tasks/26-09-18-test-sidefx-guard.md

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮 `tests/sidefx.py` 修复与知识库回写的**工作树**(同步至远端 `9f7f6b82` 之后的收尾树)。
- `commands run test.full` 实测(wrapper 墙时 158.4s, 2026-11-02 22:23 采样, Windows 本机):
  - 汇总行: `4883 passed, 2 skipped, 3 warnings in 156.60s (0:02:36)`
  - TOTAL 表: `TOTAL  22521  134  7726  128  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- **串行回归**: `commands run test.one -- tests/test_sidefx.py`(固定 `-n 0`)`12 passed`, 会话台账「越界 0」——修复前同命令为 5 failed + 6 passed + 1 error / 12 条越界假阳性。
- **收尾复跑**(最终树, 含 issue/pitfall/本片回写与坏链修正后): `4883 passed, 2 skipped, 3 warnings in 179.22s (0:02:59)`, TOTAL 同上 —— 与 22:23 采样计数一致。
- **环境注记**: 本机同期有其它 clone 的 pytest 进程在跑(多 clone 并行), 本轮零失败、零偶发红。

## 本改动面

- 测试基建 `tests/sidefx.py`: 删除导入时固化的 `TEMP_ROOTS = _temp_roots()`; 新增 `_roots_signature()`(取
  `gettempdir()` + `TMPDIR/TEMP/TMP`)与 `_ROOTS_CACHE` 签名失效; `is_temp_path` 改为按当前根集合判定。
- 测试 `tests/test_sidefx.py`: 新增 `test_sidefx_temp_roots_follow_tmpdir_switch`(陈旧快照 + 切 `TMPDIR` 后必须重算),
  头部「## 测试计划」同步追加条目。
- 知识库回写: 本基线切片 + issue [`26-11-02-2142`](../../issues/26-11-02-2142-test-sidefx-serial-false-positive.html)
  (`issue-status=Done` + 状态日志 + `doc-refs` 追加本片) + 任务档案 `26-09-18-test-sidefx-guard.md`
  (Refs / 进度日志) + 新坑 `pitfalls/testing/sidefx-import-time-temp-roots.md` + `testing/file-conventions.md` sidefx 段。
- 生产代码: **零 `src/` 改动**; `config.yml` / `auto-qb-data/` 红线未触碰; 未跨仓库; 未扩池。
