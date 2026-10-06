# 2678 —— 扩展选项页明细表时间补日期 (@ 开发中, 未提交)

> 摘要: 本轮只动 `extensions/hr-fetch-proxy/options.js` 的 `shortTime()` —— 时间格式
> `HH:MM:SS` → `MM-DD HH:MM:SS`(事件环最近 50 条会跨天, 只有时分秒分不清是哪天)。
> 该文件不进 `--cov=src` 的 Python 统计, 也不在 `testpaths(tests/)` 内 ⇒ 语句 / 未覆盖 /
> 分支 / partial 与上一条 [26-10-06-1902](26-10-06-1902-docs-ui-smoke-comment-residue.md)
> 的差异全部来自并行会话已入库的提交(语句 16021 → 15823), 与本轮无关。
> 基线时间: 2026-10-06 19:28

**Refs:** memory-bank/activeContext/26-10-06-1928-ext-shorttime-add-date.md

- 分支: develop @ **5bd01b65**(开工 `commands run my-commit-flow.sync` = `已同步 5bd01b65`;
  工作树含本轮 `options.js` + 知识库改动, **未提交**)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2678 passed + 4 skipped, 覆盖率 TOTAL 99%**; 耗时 **34.8s**(脚本计时,
  pytest 自报 33.89s)。
  语句 **15823** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- 相对上一条 [26-10-06-1902](26-10-06-1902-docs-ui-smoke-comment-residue.md)
  (2678 + 4 / 16021 / 163 / 5472 / 143): passed / 未覆盖 / 分支 / partial **四项逐位相同**;
  语句 **16021 → 15823(-198)** 归因于同步带入的并行会话提交(纯 Python 侧增删), 本轮改的
  `options.js` 不进覆盖率统计。
- 本轮真正验收: `commands run test.quick` 首跑 **2678 passed, 4 skipped**(改后立即全绿);
  扩展无独立 JS 测试, `tests/test_extension_proxy.py` 只守 options.js 函数落点, 不校验时间格式,
  `shortTime` 仍在落点清单语义内, 守阵不涉及。
