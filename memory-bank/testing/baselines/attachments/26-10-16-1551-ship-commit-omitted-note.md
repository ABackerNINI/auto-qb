# 3476 passed + 4 skipped —— ship.commit 子集提示与实际提交面对齐(issue 26-10-16-1523 修复)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html」。子集提交旧提示「另有 N 个改动未纳入」把已暂存的未传改动读成"没进本笔", 而 `git commit` 提交的是整个索引(入池实测: 10 个 `D ` 撤跟踪项被列成「未纳入」却全在同一笔里)。修法 = issue §06 方向 A(措辞与语义对齐, 不动提交行为; 方向 B「真正路径限定提交」不做 —— 会推翻坑档 `git/ship-commit-staged-delete.md` 已依赖的「已暂存删除项随整索引落笔」便利): `commit.py` 新增 `omitted_note()`, 按索引状态分组打印 `已暂存 N 个(仍会随整索引进本笔: …)` + `未暂存 N 个(不会进本笔: …)`(空组不列); 顺带 `omitted` 去重(MM 文件不再翻倍)。数字测在含本轮 2 个代码文件改动的工作树上(文档回写与 tests/ 采集面无交集)。
> 基线时间: 2026-10-16 15:51

**Refs:** memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html,memory-bank/activeContext/26-10-16-1533-ship-commit-omitted-note.md

- test.full: 3476 passed + 4 skipped / TOTAL 17633 语句 245 未覆盖 5990 分支 177 partial / 98%(闸门过)。耗时 169.0s(单次采样; 引擎口径 171.9s, 口径见 baseline.md)。
- 定向(本轮变更面): `commands run test.one -- .commands/my-commit-flow/scripts/test_commit.py` → **36 passed**(含新增 4 条: 去重 / 分组与计数示例 / 示例截断且空组不列 / 真仓「提示=提交面」对齐)。
- 红绿双验(3 类突变, 逐类判红后还原; 注入锚点唯一性先断言): ①打印点回退为旧「未纳入」平铺 → 真仓对齐用例红(`assert '另有 2 个改动未参与 add' in '…未纳入(base.txt、loose.txt)…'`); ②去重回退(`dict.fromkeys` 还原)→ dedup 用例红; ③分组打反(已暂存组吃掉全部未传改动)→ 分组用例 + 真仓用例红。还原后 `commit.py` SHA256 与注入前一致(`c3e7f95dc6b4a39b69c0ffef8e2e9ff182f12162adba62c37efee60c7259cbb9`)。驱动 `.openclaw/tmp/mutate_1523_driver.py`(未入库)。
- 复验/修复后探针(scratch, 未入库): `.openclaw/tmp/probe_1523_subset_note.py` 在临时仓库重放 issue §01 场景 —— 修复前: 提示「未纳入」含 base.txt 且 base.txt 就在 `git show --name-status HEAD` 里 ⇒ 仍复现; 修复后: `已暂存 1 个(仍会随整索引进本笔: base.txt); 未暂存 1 个(不会进本笔: loose.txt)`, 与提交面逐条一致。输出留档 `probe_1523_out_before.txt` / `probe_1523_out.txt`。

## 包内脚本测试(既有失败记录, 与本次改动无关)

- `commands run test.pkg`: **2 failed + 162 passed**(90.2s)。同日多次复采: 全量口径稳定 2 条, 该文件单跑 3 条 —— 失败集合随并行调度漂移。两条失败均属**既有环境问题**, 判定依据:
  - `test_find_repo_root_returns_none_outside_repo`(确定性): 本机 `R:` 盘缺失 ⇒ 约定 `TMPDIR=R:/Temp/auto-qb/tests` 失效, `tempfile` 回落 `C:\Users\11059\AppData\Local\Temp` ⇒ `_snapshot._find_repo_root` 从临时目录上溯命中**家目录杂散 `.git`**(`C:\Users\11059\.git`, 创建于 2026-09-27) ⇒ 期望 `None` 实得 `C:/Users/11059`。探针复现一致; 串行同样单发。
  - `test_import_does_not_respawn`(及间歇的 `test_snapshot_is_removed_after_run`): `-n 8` 并行下**跨 worker 互见**临时快照目录 —— 同一目录名(实例 `my-commit-flow-3o02_fz4`)同时出现在两条用例的失败断言里; 串行 `-n 0` 全文件 14 passed(仅剩家目录那条红); 运行后 `%TEMP%` 无残留(非泄漏)。仅在并行下出现, 调度一变集合即变。
  - **无关性证据**: 上述用例只加载 `_snapshot.py` / `_ship_config.py`(本轮未动, `git diff` 为空); **单跑该文件(不含本包其它脚本与本轮代码)即复现**; 本轮改动文件(`commit.py` / `test_commit.py`)不在其 import 链上。
- 只读复现命令(供后续会话/机主复核): `uv run pytest .commands/my-commit-flow/scripts/test_snapshot.py -q -n 0 --no-cov`(串行, 仅家目录 1 条红)与 `… -n 8 --no-cov`(并行, 2~3 条红)。识别口径已记坑档 `memory-bank/pitfalls/testing/tmpdir.md` 新条目「约定盘缺席/不可见 → TMPDIR 静默回落 %TEMP%」。
- Linux(WSL)侧未跑 —— 改动为纯输出文案逻辑, 无平台分支。

## 本改动面

- `.commands/my-commit-flow/scripts/commit.py`: 新增 `_sample()` / `omitted_note(omitted, staged)`(按索引状态分组, 空组不列); 打印点改 `print(omitted_note(omitted, staged))`; `resolve_stage_plan` 的 `omitted` 去重(`dict.fromkeys`); 模块 docstring 流程第 3 步与函数 docstring 同步(记 issue 26-10-16-1523)。
- `.commands/my-commit-flow/scripts/test_commit.py`: 新增 4 条用例 + 头部「测试计划」清单同步两行。
- 文档: 坑档 `git/ship-commit-staged-delete.md` 变体二补「提示已分组」一行; issue `26-10-16-1523` 置 `Done`; 会话切片 `26-10-16-1533-ship-commit-omitted-note.md`。
