# infra 修复轮 · dup-code-audit 三 issue 认领与修复（url 分解 / 小样板 / win DLL 惰性绑定）

> 摘要: 用户「认领并修复: 26-10-11-0352-refactor-infra-url-decompose-dup / -infra-utils-small-helper-dup / -infra-win-dll-lazy-bind-dup」→ 对 dup-code-audit 专题 infra 轮(R18)入池的 3 条 refactor issue 认领并修复, 全部置 `Done`。口径沿用前几轮(hr/webui/rules/core): A/C 类抽单点收敛, 保守口径(行为逐字不变, 既有守阵回归)。实际修法: ①`utils._split_url(url) -> (scheme, netloc, path, query)` 分解单点(去 userinfo / 缺 scheme path 首段兜底且首段消费后不回填 / 失败 None), `sanitize_tracker_url` 与 `mask_tracker_url` 共用(原建议形态, 零改道); ②`utils._hosts_of(urls)` 收敛 host 收集内联循环(条目 dict 列表经生成器适配), `file_access` 基类 `FileAccess._probe(os_fn, path)` + `_probe_path` 收编 exists/isdir/isfile 三连 —— 探针单点形态与原建议略有出入: os 判定三连收在基类, Local/Mapped 只实现 `_probe_path` 给 syscall 路径(原建议「各类传自己的 fn」抽完后基类仍留三份定义, 收口不彻底); ③`utils._win_dll(name, sigs)` 参数化惰性绑定骨架, `_bound_*` 全局与 monkeypatch 注入点保留, `is_windows()` 早退在缓存判定之前, 新增 `_WIN_KERNEL32_SIGNATURES()` 同 user32 口径。**连带修订**: 三态探针收编后 `os.path.exists` 由调用变基类属性引用, 静态守阵 `test_fs_mock_coverage_static_guard` 首轮全量红验(期望表未同步) —— 按守阵自身规矩更新 `_EXPECTED_PROBES`(去掉 exists 钉计数, 注释说明)与 `sim_fsmock.MockCoverage` 覆盖说明后复绿; mock 按模块属性打桩, 覆盖实质不变。infra 余 2 条(`infra-fmt-ladder-dup` / `infra-platform-detect-bypass-dup`)不在本轮范围, 留 `Open`。
> 最后活动: 2026-10-12 21:25

**Refs:** memory-bank/issues/26-10-11-0352-refactor-infra-url-decompose-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-utils-small-helper-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-win-dll-lazy-bind-dup.html

## 已完成(2026-10-12 单会话收口)

- 三份 issue 复验(锚点均在, win-dll 行号漂移按 grep 事实定位)后置 `In Progress`, 修复完成置 `Done`, 状态变更日志逐条留痕(含实际修法/验证方式/测试数字)。
- 改动面: `src/auto_qb/infra/utils.py`(_split_url / _hosts_of / _win_dll + _WIN_KERNEL32_SIGNATURES) + `src/auto_qb/infra/file_access.py`(_probe/_probe_path) + `tests/test_sim_corpus.py`(静态守阵期望表) + `scripts/sim_fsmock.py`(MockCoverage 覆盖说明); 全部过 `dev.fmt`。
- 验证: 定向 `test_utils.py` + `test_file_access.py` 全绿; 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/26-10-12-2125-infra-dup-code-fixes.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- 未 commit / 未 push(用户未要求); 重复代码审查主线(Phase 2 前端轮 20–23 / Phase 3 测试横切 24–25 / Phase 4 汇总 26)仍未开工。
