# 单文件跑测试时覆盖率门槛假红 (test.one / 裸 pytest <file>)

> 摘要: 只跑单个测试文件时(无论 `commands run test.one -- tests/x.py` 还是裸 `uv run pytest tests/x.py -q`), 全部用例绿但收尾仍打 `FAIL Required test coverage of 98% not reached. Total coverage: 18%` —— 这是覆盖率**全局门槛**只对全量收集有意义, 单文件跑必然红, 用例本身全过; 判据看 `N passed` 行, 不要被 FAIL 行骗去修代码。
> 触发: test.one, 单文件, 单测一个文件, coverage FAIL, not reached, 18%, 假红, 排查单个用例

### 单文件跑测试收尾出现 `FAIL Required test coverage of 98% not reached`

- **触发**: 改完某个测试文件想快速验证, 跑 `commands run test.one -- tests/<file>.py` 或裸 `uv run pytest tests/<file>.py -q` (2026-10-04, 导航页守阵 test_kb_nav.py 首跑实测: `9 passed` 与 `FAIL ... Total coverage: 18.41%` 同屏)。
- **判别**: 输出里**同时**有 `N passed`(全绿) 与末尾覆盖率 FAIL —— 根因是 pytest.ini / pyproject 的 `--cov-fail-under=98` 作用于**本次收集面**的覆盖率: 只收集一个文件时全仓 14k+ 语句只有少数被执行, 总覆盖率必然远低门槛; 这与用例成败无关。真失败看 `FAILED` / `errors` 行, 没有它们就是全过。
- **处置**: 单文件验证以 `N passed` 为准, 忽略覆盖率 FAIL 行; 要一个干净的绿灯结论就跑 `commands run test.quick`(全量收集 + `--no-cov`, ~7s)或收尾时跑 `test.full`。不要为消掉这行去给单文件运行加 `--no-cov` 之外的动作(如调低门槛) —— 门槛是全量基线的守卫, 只属于全量跑。
