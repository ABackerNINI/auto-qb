# 2685 —— WebUI perf 双 issue 复验收尾 (develop @ 20bd2157, 文档轮)

> 摘要: 复验 26-09-19-2122(节拍门控双生产者)与 26-09-21-1408(四视图全量重建)两条 issue——重构后
> 锚点全失效, 逐符号重定位核对, 两条均仍成立、Open 维持; 产出复验报告 26-10-07-0054 + 两条 issue
> 复验行/锚点刷新 + 任务档案 26-10-07-webui-perf-issues-recheck + 认领链双向补齐。本轮**纯
> memory-bank 文档, `src/` 零改动** ⇒ 覆盖四项与上一条逐位相同。
> 基线时间: 2026-10-07 01:20

**Refs:** memory-bank/activeContext/26-10-07-0115-webui-perf-issues-recheck.md, memory-bank/tasks/26-10-07-webui-perf-issues-recheck.md

- 分支: develop @ **20bd2157**(开工 `commands run my-commit-flow.sync` = 快进 d96169aa→20bd2157,
  远端领先 7 笔; 本轮尚无本地提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2686 passed + 4 skipped, 覆盖率 TOTAL 99%(98.53%)**; pytest 自报 **37.72s**。
  语句 **15823** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- 相对上一条 [26-10-06-2027](26-10-06-2027-webui-esc-order-history-first.md)
  (2682 + 4 / 16021 / 163 / 5472 / 143): passed **+4** 全来自开工同步入库的远端提交(errlog 端点等,
  11667c95 一族); 语句 16021→**15823**(-198, 同批重构); 未覆盖 / 分支 / partial 三项**逐位相同**;
  覆盖率 99% 持平。本轮改动全部在 `memory-bank/`(HTML 报告 + issue + 档案 + 切片), 不进
  `--cov=src` 统计。
- 过程注记: 首两轮 test.full 红于 `test_claim_chain_is_bidirectional`(档案 Refs 指向的报告/issue
  未反向声明 + 基线切片未建)与 4 条 tasks 索引守阵(kb.index 未重跑)——均为**收尾步骤未完成**的
  预期中间态, 补齐后转绿; 数字以本轮为准。
