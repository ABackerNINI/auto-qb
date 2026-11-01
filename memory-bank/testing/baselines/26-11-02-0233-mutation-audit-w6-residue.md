# 4805 passed + 2 skipped —— 全量测试基线: W6 残留两 issue 收口(变异命令包轮次参数账本)

> 摘要: 全量测试基线: W6 残留两 issue 收口(变异命令包轮次参数账本)
> 基线时间: 2026-11-02 02:33
**Refs:** memory-bank/issues/26-11-01-0614-test-core-w6-mutation-notests-offpool.html, memory-bank/issues/26-11-01-0614-test-core-w6-mutation-timeout-doubt-ledger.html

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮命令包改动的**未提交工作树**(HEAD `bd6c8a32` + `.commands/mutants` 改动与知识库回写件)
- `commands run test.full` 实测(wrapper 墙时 195.7s, 2026-11-02 02:31, Windows 本机):
  - 汇总行: `4805 passed, 2 skipped in 192.19s (0:03:12)`
  - TOTAL 表: `TOTAL  22482  164  7708  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- 包内脚本测试: `commands run test.pkg.scoped -- .commands/mutants` → `[ok] test.pkg.scoped (4.9s)`, 包内 `24 passed in 3.77s`(基线 18 + 本轮新增 6 条: 4 条 `set_conf` 渲染 / 2 条结果头账本)
- 形态级探针(issue 2 复验, WSL mutmut 3.8.0 镜像): 4 条 TypeError 变异 × 2 池 = **8/8 `rc=124` @120s 硬超时**; 两池基线均绿(W6 池 `257 passed in 24.31s`(墙 25.13s) / WIDE 池 `506 passed, 1 skipped in 51.51s`(墙 52.47s))
- **环境 / 工具**: Windows 本机(win32)· Python 3.13 · `TMPDIR` 由 `test.full` 包内内置; 探针在 WSL Ubuntu-26.04 + mutmut 3.8.0
- **口径注记**: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。本轮**未重跑 W6 整轮变异**(只做形态级探针), 故本切片不含新的轮次杀死率。

## 本改动面

- `.commands/mutants/scripts/set_conf.py`: `timeout_multiplier` 显式写入 `[tool.mutmut]`(默认 `DEFAULT_TIMEOUT_MULTIPLIER = 15.0`, 与 mutmut 默认一致); 新增 `--timeout-multiplier` 参数透传 `render()`; 修掉「镜像手工值被覆盖式重写静默抹掉」的不可复现面。
- `.commands/mutants/scripts/mutants.py`: `run` 新增 `--timeout-multiplier`(非正值 fail-fast)并透传给 `set_conf`; 新增 `_run_header` / `_write_results` 账本头 —— 非 dry-run 时查镜像 `git rev-parse --short HEAD` 与 `mutmut --version`, 结果文件头写 `target / children / timeout_multiplier / pool 清单 / 镜像 HEAD / 工具版本`。
- `.commands/mutants/scripts/test_mutants.py`: 新增 `SetConfRenderTest`(4 条: 显式写倍数 / 默认 15.0 / 重写无残留 / 非正值拒绝)与 `RunHeaderTest`(2 条: 账本字段 / `#` 行不与 `@@@` 明细冲突); docstring「## 测试计划」同步。
- `.commands/mutants/config.toml` / `references/why.md`: 命令说明补 `--timeout-multiplier` 与「轮次参数与账本」口径段(no-tests 是池的函数, TIMEOUT 是超时倍数的函数)。
- 知识库回写: 两 issue HTML(状态 `Done` + 复验 / 修法 / 验证 / 遗留分别登记)、任务档案 `26-10-08-test-mutation-audit.md` 追加 R37、本切片与索引重建。
- 零 `src/` 改动(未改主循环异常吞没、未改池); `config.yml` / `auto-qb-data/` 红线未触碰。
