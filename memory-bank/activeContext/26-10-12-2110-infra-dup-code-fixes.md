# infra 修复轮 · dup-code-audit issue 认领与修复（url 分解 / 小样板 / win DLL 惰性绑定 / 平台判定单点）

> 摘要: 用户「认领并修复: 26-10-11-0352-refactor-infra-url-decompose-dup / -infra-utils-small-helper-dup / -infra-win-dll-lazy-bind-dup」→ 对 dup-code-audit 专题 infra 轮(R18)入池的 3 条 refactor issue 认领并修复, 全部置 `Done`。口径沿用前几轮(hr/webui/rules/core): A/C 类抽单点收敛, 保守口径(行为逐字不变, 既有守阵回归)。实际修法: ①`utils._split_url(url) -> (scheme, netloc, path, query)` 分解单点(去 userinfo / 缺 scheme path 首段兜底且首段消费后不回填 / 失败 None), `sanitize_tracker_url` 与 `mask_tracker_url` 共用(原建议形态, 零改道); ②`utils._hosts_of(urls)` 收敛 host 收集内联循环(条目 dict 列表经生成器适配), `file_access` 基类 `FileAccess._probe(os_fn, path)` + `_probe_path` 收编 exists/isdir/isfile 三连 —— 探针单点形态与原建议略有出入: os 判定三连收在基类, Local/Mapped 只实现 `_probe_path` 给 syscall 路径(原建议「各类传自己的 fn」抽完后基类仍留三份定义, 收口不彻底); ③`utils._win_dll(name, sigs)` 参数化惰性绑定骨架, `_bound_*` 全局与 monkeypatch 注入点保留, `is_windows()` 早退在缓存判定之前, 新增 `_WIN_KERNEL32_SIGNATURES()` 同 user32 口径。**连带修订**: 三态探针收编后 `os.path.exists` 由调用变基类属性引用, 静态守阵 `test_fs_mock_coverage_static_guard` 首轮全量红验(期望表未同步) —— 按守阵自身规矩更新 `_EXPECTED_PROBES`(去掉 exists 钉计数, 注释说明)与 `sim_fsmock.MockCoverage` 覆盖说明后复绿; mock 按模块属性打桩, 覆盖实质不变。infra 余 2 条(`infra-fmt-ladder-dup` / `infra-platform-detect-bypass-dup`)不在本轮范围, 留 `Open`。**第二轮(2026-10-15, 用户指派「认领并修复」第 4 条)**: `infra-platform-detect-bypass-dup` 复验锚点均在后置 `Done` —— 7 处旁路(`infra/autostart.py` 6 处 + `tray/app.py` 1 处)全改走 `utils.is_windows()/is_mac()` 单点(零行为变化, `is_windows` 的 "win" 前缀已覆盖旁路的 "win32"), 新增静态守阵 `test_platform_detect_single_point_static_guard`(src/ 全域禁裸 `sys.platform.startswith`, 单点自身豁免); infra 余 1 条(`infra-fmt-ladder-dup`)仍留 `Open`。详见下方第二轮段。
> 最后活动: 2026-10-15 04:22

**Refs:** memory-bank/issues/26-10-11-0352-refactor-infra-url-decompose-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-utils-small-helper-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-win-dll-lazy-bind-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-platform-detect-bypass-dup.html

## 已完成(2026-10-12 单会话收口)

- 三份 issue 复验(锚点均在, win-dll 行号漂移按 grep 事实定位)后置 `In Progress`, 修复完成置 `Done`, 状态变更日志逐条留痕(含实际修法/验证方式/测试数字)。
- 改动面: `src/auto_qb/infra/utils.py`(_split_url / _hosts_of / _win_dll + _WIN_KERNEL32_SIGNATURES) + `src/auto_qb/infra/file_access.py`(_probe/_probe_path) + `tests/test_sim_corpus.py`(静态守阵期望表) + `scripts/sim_fsmock.py`(MockCoverage 覆盖说明); 全部过 `dev.fmt`。
- 验证: 定向 `test_utils.py` + `test_file_access.py` 全绿; 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/26-10-12-2125-infra-dup-code-fixes.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- 未 commit / 未 push(用户未要求); 重复代码审查主线(Phase 2 前端轮 20–23 / Phase 3 测试横切 24–25 / Phase 4 汇总 26)仍未开工。

## 第二轮(2026-10-15 单会话收口 · 用户指派「认领并修复」第 4 条)

- issue `26-10-11-0352-refactor-infra-platform-detect-bypass-dup`: 复验锚点均在(grep `sys.platform.startswith` = autostart.py 6 处 + tray/app.py:204; 单点口径 `"win"` 前缀, 旁路口径 `"win32"`)后置 `In Progress` → 修复完成置 `Done`, 状态变更日志逐条留痕(含实际修法/验证方式); 认领链双向(本切片 Refs ↔ issue doc-refs)。
- 修法(取 issue「建议」第一支, 零行为变化): `infra/autostart.py` 6 处(`is_enabled`/`enable`/`disable` 的 win/darwin 分支)经包内相对导入 `from .utils import is_mac, is_windows` 改调 `is_windows()`/`is_mac()` —— `is_windows` 匹配 `"win"` 前缀已覆盖 `"win32"`, 语义逐字等价; `sys` 导入保留(`sys.executable` 仍用)。`tray/app.py:204` 改调 `utils.is_windows()`(模块级已导入 utils), `import sys` 随之移除(该文件唯一用途)。未采纳「抽 `_platform()` 枚举」支: 调用点改函数调用即收口, 枚举是新抽象面, 保守口径不扩。
- 新增静态守阵 `tests/test_utils.py::test_platform_detect_single_point_static_guard`: 扫 src/ 全部 .py 禁裸 `sys.platform.startswith`(单点自身豁免; notify.py 取平台字符串值作标识非 startswith 判据, 不拦); 红验 = 临时注入旁路判红后删除临时文件。
- 改动面: `src/auto_qb/infra/autostart.py` + `src/auto_qb/tray/app.py` + `tests/test_utils.py`(守阵 + 测试计划清单同步) + 本 issue 状态流转; 全部过 `dev.fmt`。
- 验证: 定向 `test_utils.py`+`test_ui.py`+`test_tray.py` 全绿(coverage 未达标为子集运行预期); 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/26-10-15-0422-infra-platform-detect-bypass-dup.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- infra 余 1 条(`infra-fmt-ladder-dup`)仍留 `Open`。
