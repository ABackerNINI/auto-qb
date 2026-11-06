# 5479 —— 修复 GitHub CI Windows 码页六红: 文本子进程显式 UTF-8 + 全仓 AST 守阵

> 摘要: 修复 GitHub CI Windows 码页六红: 文本子进程显式 UTF-8 + 全仓 AST 守阵
> 基线时间: 2026-11-06 19:50
**Refs:** memory-bank/tasks/26-11-06-test-windows-codepage-ci.md

## 验收数字

`commands run test.full` 实测(TMPDIR 须清空后跑, 见 pitfalls/testing/tmpdir.md):

- 汇总行: `5479 passed, 2 skipped, 1 warning in 134.12s (0:02:14)`
- 覆盖率: `Required test coverage of 99.5% reached. Total coverage: 99.71%`(门槛 99.5%, Windows 档)
- TOTAL 表: 24538 statements / 57 miss / 8396 branch / 36 partial / 99%
- 覆盖率行取自同一棵树全量 pytest 原始输出(展开形态由 `commands show test.full` 单点查询, 文档不抄命令) —— 引擎对 `test.full` 声明 `silent_success`, 成功只透传结论行, 覆盖率明细需主动另取全量输出。
- 常规 `test.quick`: 5479 passed, 2 skipped; `PYTHONUTF8=0` 模拟 CI 码页 `test.quick`: 5478 passed, 3 skipped。
- `test.pkg`: 353 passed + 15 subtests; review 包 `test.pkg.scoped`(格式化后复验): 69 passed。
- 守阵 + 测试计划守卫: 11 passed; 受影响 6 文件(`PYTHONUTF8=0`): 86 passed; 6 条原 CI 红用例: 6 passed。
- `kb.check` 十道校验全绿; 全仓文本模式 subprocess 调用严格审计(校验字面量值): 48 处、0 不合规。

## 本改动面

- **收端修复(16 处)**: `tests/test_kb_nav_interaction.py`(4 处补 `errors="replace"`, 抽 `NODE_PROBE_TIMEOUT = 60`)、`tests/test_webui_config_normalize_parity.py`(1)、`tests/test_webui_relocate_chain.py`(1)、`tests/test_webui_relocate_visibility.py`(2)、`tests/test_webui_static_dom_page_layout.py`(7)、`tests/webui_static_scan_js.py`(1) —— 全部显式 `encoding="utf-8", errors="replace"`。
- **守阵**: `tests/test_platform_tolerance_guards.py` 新增全仓 AST 对账 `test_repo_text_subprocess_calls_pin_utf8` + 合成源活性探针 `test_text_subprocess_checker_liveness`; 按函数名罩住 `run`/`check_output`/`check_call`/`Popen` 两种 import 形态, 评审后升级为校验 `encoding`/`errors` 的字面量值, 并堵掉 `text=None` 短路 `universal_newlines=True` 的漏报。
- **坑档**: `memory-bank/pitfalls/ops/console-encoding.md` 口径收成两项必填 + `复发 +1`; `memory-bank/pitfalls/testing/ci-only-guard.md` 补解码侧第 ⑤ 变体 + 反面证据/复现局限。
- **评审连带**: `.commands/review/scripts/check_review_trace.py` 与 `test_review_pkg.py` 各一处非 ASCII 图形符号改 ASCII。
- **格式化**: 提交闸门 `dev.fmt` 因本批含 `tests/` 改动而触发, 顺带把两份既有 `.commands/review/scripts/*.py` 格式化到项目 yapf 口径(其 HEAD 版本本就不合规); 二次 `yapf -d` 零漂移。
- 零产品/运行时代码改动, `.github/workflows/ci.yml` 未触碰。
