# 单文件跑测试时覆盖率门槛假红 (test.one / 裸 pytest <file>)

> 摘要: 只跑单个测试文件时, 全部用例绿但收尾仍打 `FAIL Required test coverage of <门槛>% not reached. Total coverage: ~18%` —— 覆盖率**全局门槛**只对全量收集有意义, 部分运行收集面小必然红, 用例本身全过。**`commands run test.one` 已内置 `--no-cov`(2026-10-05 修复)**, 该假红此后只在**裸跑** `uv run pytest tests/x.py -q` 时仍会出现; 判据看 `N passed` / `FAILED` 行, 不要被 FAIL 行骗去修代码。
> 等级: L0
> 触发: test.one, 单文件, 单测一个文件, coverage FAIL, not reached, 18%, 假红, 排查单个用例, 裸跑 pytest 单文件

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md

### 单文件跑测试收尾出现 `FAIL Required test coverage of 98% not reached`

- **触发**: 改完某个测试文件想快速验证, 裸跑 `uv run pytest tests/<file>.py -q`; 2026-10-05 前 `commands run test.one -- tests/<file>.py` 同命中 (导航页守阵 test_kb_nav.py 首跑实测: `9 passed` 与 `FAIL ... Total coverage: 18.41%` 同屏)。
- **判别**: 输出里**同时**有 `N passed`(全绿) 与末尾覆盖率 FAIL —— 根因是覆盖率阈值作用于**本次收集面**的覆盖率: 只收集一个文件时全仓 14k+ 语句只有少数被执行, 总覆盖率必然远低门槛; 这与用例成败无关。真失败看 `FAILED` / `errors` 行, 没有它们就是全过。**阈值位置已迁**: 原 `pytest.ini` 的 `--cov-fail-under=98` 于 2026-10-30 移到 `tests/conftest.py::pytest_configure`(Windows 99.0 / 其它 98.5, 见 [coverage-floor-platform.md](coverage-floor-platform.md)), 判据不变 —— 报错行里的百分比只是把 `99.0%` / `98.5%` 换个数字。
- **处置**: `commands run test.one` 已内置 `--no-cov`, 直接用它就没有这行(2026-10-05, issue 26-10-05-0922-chore-pytest-cov-gate-test-one —— 改动只在 task 定义, 闸门原样保留给 `test.full` 与 CI 全量跑); 裸跑 `uv run pytest <file>` 时手工加 `--no-cov`, 或以 `N passed` 为准忽略 FAIL 行。要一个干净的绿灯结论就跑 `commands run test.quick`(全量收集 + `--no-cov`, ~7s)。**不要为消掉这行去调低门槛** —— 门槛是全量基线的守卫, 只属于全量跑。
- **复发**: 3 —— ① 2026-10-05 (webui-danger-guards S5 红验抽查, 计划 26-10-05-0314 收尾): 红验探针两次单文件跑(`test.one -- tests/test_ops.py -k …` / `tests/test_web_*.py -k …`)同屏出现 `1 failed`(真红, 探针意图)与 `FAIL Required test coverage of 98% not reached. Total coverage: 21.37%`(假红)—— 本次**命中但已知**: 判据「`N passed`/`FAILED` 行与 FAIL 行分开看」直接套用, 假红未造成误判; 没有提前规避是因为红验就要单跑单条用例, 单文件收集面下该 FAIL 必然出现, 属预期噪声非新坑。② 2026-10-05 认领 issue 26-10-05-0922 按防过期原则第 5 条复验: `test.one -- tests/test_docs_forms.py` 仍 `11 passed` + `FAIL ... Total coverage: 18.52%` 同屏 —— 本次**故意复现**(修复前必须先确认现象仍在), 非误判。③ 2026-10-16 (global-traffic-monitor S6 红验, 计划 26-10-16-0541): 自建红验 harness 用**裸** `python -m pytest <target>`(不走 `test.one` 的 `--no-cov`)跑单条用例 —— 突变前基线 7 条全被打成 FAIL(末行是覆盖率 `No data was collected.` 而非 `N passed`), 一度像「基线不绿」; 处置 = harness 对 auto-qb 侧加 `--no-cov -n 0`(工具侧 pytest 无覆盖率闸, 只 `-q`)。**未命中原因**: 该 harness 是照抄 S5 红验脚本改的, 只搬了「钉死解释器/字节层」两条纪律, 漏了「单文件跑必须绕覆盖率闸」这条 —— 红验脚本的调用参数不是 `test.one`, 判据要自己补齐。
