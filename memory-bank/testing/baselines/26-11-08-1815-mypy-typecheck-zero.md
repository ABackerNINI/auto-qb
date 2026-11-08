# 5847 passed + 2 skipped(根) —— dev.typecheck 归零后基线

> 摘要: dev.typecheck 归零后基线
> 基线时间: 2026-11-08 18:15

## 验收数字

`commands run test.full`(2026-11-08, 分支 develop @ f674ce4a):

```text
TOTAL                                                26065     33   9050     51    99%
5847 passed, 2 skipped, 15 warnings in 162.63s (0:02:42)
```

另: `commands run dev.typecheck` → Success: no issues found in 196 source files(3 条 annotation-unchecked note 属既有, 非 error); `dev.fmt` 后复跑仍零错。

## 本改动面

- src/auto_qb/hr/model.py: HrWaveMeta / HrSiteData.from_json 三处容器形状守卫改局部变量 + isinstance 收窄
- src/auto_qb/infra/relocate_journal.py: write_daemon_state / touch_daemon_state 的 body 加 Dict[str, object] 注解; reset_rewrites 的 rewrites 改局部变量收窄
- src/auto_qb/infra/alias_fs.py: retarget_alias 的 form 加非空守卫收窄(运行时不可达, fail-fast 兜底)
- src/auto_qb/tools/recycle_daemon.py: _scan_jobs / _process_window 三处 rewrites / prev 改局部变量收窄
- src/auto_qb/webui/relocate_chain.py: finalize_face 的 rewrites 改局部变量收窄
- 记账面: issue 26-11-08-0118 翻 Done + 立档 / 切片 / 坑档; pyproject.toml 与 tests/test_mypy_allowlist_guard.py 零改动
