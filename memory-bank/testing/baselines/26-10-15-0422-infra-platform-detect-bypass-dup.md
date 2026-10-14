# 3207 — infra 平台判定旁路单点修复（dup-code-audit 第 4 条）实施基线

> 摘要: 用户指派「认领并修复: 26-10-11-0352-refactor-infra-platform-detect-bypass-dup」→ 平台判定单点 `utils.is_windows/is_linux/is_mac/is_posix` 的 7 处旁路（`infra/autostart.py` 6 处 + `tray/app.py` 1 处裸 `sys.platform.startswith("win32"/"darwin")`，与单点 `"win"` 前缀口径不一致）全改走单点，保守口径（零行为变化: `is_windows` 匹配 `"win"` 前缀已覆盖 `"win32"`，语义逐字等价）。修法（取 issue「建议」第一支）: `autostart.py` 经包内相对导入 `from .utils import is_mac, is_windows` 改调 `is_windows()`/`is_mac()`（`sys` 导入保留 —— `sys.executable` 仍用）; `tray/app.py` 改调 `utils.is_windows()`（模块级已导入 utils）并移除 `import sys`（该文件唯一用途）。未采纳「抽 `_platform()` 枚举」支: 调用点改函数调用即收口，枚举是新抽象面，保守口径不扩。新增静态守阵 `tests/test_utils.py::test_platform_detect_single_point_static_guard`（扫 src/ 全域禁裸 `sys.platform.startswith`，单点自身豁免; notify.py 取平台字符串值作标识非 startswith 判据不拦），红验 = 临时注入旁路判红后删除临时文件。
> 基线时间: 2026-10-15 04:22（修复实施后收口）

**Refs:** memory-bank/activeContext/26-10-12-2110-infra-dup-code-fixes.md,memory-bank/issues/26-10-11-0352-refactor-infra-platform-detect-bypass-dup.html

## test.full 实测

- 分支: `develop`（会话开工 `my-commit-flow.sync` 已同步 4d268762; 工作树含本批次全部改动时实测）
- 命令: `commands run test.full`
- **实测 (Windows)**: **3207 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16840 语句 / 162 未覆盖 / 5728 分支 / 143 partial; 门槛 98% 达标; 本轮 165.5s)
- 前置机检: 定向 `tests/test_utils.py` + `tests/test_ui.py` + `tests/test_tray.py` 全绿（coverage 未达标为子集运行预期）; 首轮 test.full 曾红 `test_claim_chain_is_bidirectional`（issue doc-refs 已指向切片、切片 Refs 未回列本 issue = 认领链单向）—— 切片 Refs 补列本 issue 后复绿; 守阵红验 = 临时注入旁路判红后删除; 改动文件 `dev.fmt` 全量格式化通过。
- 改动面(摘要): `src/auto_qb/infra/autostart.py`（6 处旁路改单点调用） + `src/auto_qb/tray/app.py`（1 处旁路改单点调用 + 移除 import sys） + `tests/test_utils.py`（静态守阵 + 测试计划清单同步） + `memory-bank/issues/` 1 条状态流转 + activeContext 切片续写。见 kb.baseline。
