# 仓库快照放进树内

> 摘要: 做只读评审要导出整棵仓库快照时, 快照必须放仓库**外** —— 树内的副本会让"单点定义"守卫扫到散落实现, `test.full` 直接红两条, 而快照目录明明已 gitignore。
> 触发: 快照, snapshot, git archive, 只读评审, review.lane.start, 批量评审, test-results 放快照, 单点守卫红, test_free_port, test_tmp_bootstrap, 散落

**Refs:** memory-bank/reports/26-11-06-0723-report-review-capacity-experiment.html

### 快照放 `test-results/` 会让单点守卫判红(即使该目录已 gitignore)

- **触发**: 为做只读评审 / 批量评审, 把 `git archive <sha> | tar -x -C <dir>` 解到仓库内的某个 gitignored 目录(如 `test-results/review-exp/snap-*`)。
- **判别**: `tests/test_free_port.py::test_free_port_single_source` 与 `tests/test_tmp_bootstrap.py::test_candidates_single_source` 报「散落」, 命中路径全在 `<快照>/tests/_test_ports.py`、`<快照>/tests/_tmp_bootstrap.py`。守卫是**扫全树**(不读 `.gitignore`), 所以「已忽略」不等于「看不见」—— 这两条守卫守的正是「同一个常量只能有一处定义」, 而快照里天然有第二处。
- **处置**: 快照一律放仓库外(`<repo>/../_review-exp-snap/<name>/`); 已经放进树内的移走即可。**不要**去放宽守卫(放宽等于放弃单点保证), 也不要给守卫加"跳过 test-results"的白名单(下一次换目录又会复发)。
- **复发形态提示**: 任何"整棵仓库的副本"都会撞同一堵墙 —— 备份目录、对照实验的基线树、旧版本解包。判据统一: 只要副本里有 `tests/_test_ports.py` 或 `tests/_tmp_bootstrap.py`, 就不许待在树内。
