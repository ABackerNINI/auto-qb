# 22860 —— download-fuse S4 收尾: 4957 passed / 99%

> 摘要: download-fuse S4 收尾: 4957 passed / 99%
> 基线时间: 2026-11-03 09:56
**Refs:** `memory-bank/plans/26-11-03-0456-plan-skip-check-download-fuse.html`

## 验收数字

```text
[ok] test.full (147.7s)
  TOTAL                                                22860    182    7892    157    99%
  4957 passed, 10 skipped, 3 warnings in 145.11s (0:02:25)
```
Windows 本机单次采样; Linux(WSL) 侧未重测。

## 本改动面

- `src/auto_qb/cli.py`: `fuse_release` 在 `ctx.fuse.release` 前补 `store.apply_sync`(一次性 CLI 进程快照为空, 否则 CAS 读不到当前限速 → 只标记 released 不恢复)。
- `tests/test_fuse_mod.py`: 新增 `test_fuse_release_cli_syncs_snapshot_before_cas`(锁定「先同步后放行」顺序)。
- 文档回写: 计划 §05/§3.8/§07/§10 消漂移(`fuse_tag` 配置键、released 不重加)、新增 §10.1 真机验收记录; `config-reference/keys.md` 行为段; `progress/implemented-core.md` 新增条目; `conventions/modules.md` 装配序与模块计数; 根 `README.md` 模块清单; 两处配置注释去「仅配置面」。

