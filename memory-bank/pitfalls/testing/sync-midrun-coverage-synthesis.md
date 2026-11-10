# test.full 运行中 sync 换树 → 覆盖率合成失真误红

> 摘要: test.full(xdist+coverage)运行期间执行 `my-commit-flow.sync` 快进换入远端新代码 —— 已启动的 worker 仍持旧模块字节码跑完全程, 新增/改动的源码行从未被执行, coverage 合成时这些行全记 miss, 总覆盖率跌破 99.5% 闸门误红(实测: relocate_exec miss 15→110 / relocate_proof 0→50, TOTAL 99.69%→98.68%)。测试结果本身全绿, 红的只是覆盖率合成 —— 但这一轮 135s 白烧且基线切片不能取数。
> 触发: test.full 运行中, 评审 pack 前置 sync, 会话中途 sync, 覆盖率误红, 覆盖率跌破闸门, miss 数暴涨, 基线取数

- **触发**: 后台跑 `test.full` 期间, 主会话因评审 pack 前置(或任何理由)跑 `my-commit-flow.sync`, 且远端恰有改 `src/` 的新提交快进进来。
- **判别**: 覆盖率报告 miss 数对不上上一轮量级(单文件 miss 从个位数跳到几十/上百), 且被换文件(Stmts 列变化)恰是远端新提交改的文件; 测试本身 passed/failed 全绿或仅有与本批无关的红。Stmts 列与上一轮不同 = 文件在运行中被换过, 直接实锤。
- **处置**: 丢弃该轮覆盖率, 树冻结后重跑 test.full 取数(全绿 + 覆盖率达标那轮才是基线切片的取数轮)。预防: test.full 运行期间不做任何改 `src/`/`tests/` 的树操作(sync/rebase/checkout); 簿记类(记忆库/issue)编辑无碍。评审 pack 前置 sync 应排在 test.full 取数轮**之前**完成。
