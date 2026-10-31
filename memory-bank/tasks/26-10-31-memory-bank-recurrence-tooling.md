# 26-10-31-memory-bank-recurrence-tooling — 复发榜堆3四件机械化: e2e自检/doc-refs双向/写盘形态守卫/聚合内容映射

**Status:** In Progress
**Added:** 2026-10-31
**Updated:** 2026-11-01
**Summary:** 复发榜堆3四件机械化: e2e自检/doc-refs双向/写盘形态守卫/聚合内容映射
**Topics:** memory-bank-recurrence-tooling
**Refs:** memory-bank/issues/26-10-31-2226-feat-e2e-smoke-env-selfcheck.html, memory-bank/issues/26-10-31-2226-feat-kb-docrefs-bidirectional-automation.html, memory-bank/issues/26-10-31-2226-feat-repo-writeform-guard.html, memory-bank/issues/26-10-31-2226-feat-webui-agg-content-map.html, memory-bank/testing/baselines/26-11-01-0010-recurrence-tooling-closeout.md, memory-bank/activeContext/26-11-01-0010-memory-bank-recurrence-tooling.md

## 原始请求

1. 「认领并实施」四条 issue（均出自 R4 三堆报告堆 3 立项建议）:
   - `26-10-31-2226-feat-e2e-smoke-env-selfcheck` —— e2e/冒烟环境开机自检（端口占用/旧桩进程/npm i 缺失前置探测）
   - `26-10-31-2226-feat-kb-docrefs-bidirectional-automation` —— doc-refs 认领链写法机械化（生成器/模板接管双向声明）
   - `26-10-31-2226-feat-repo-writeform-guard` —— 写盘形态守卫（行数/bytes-per-line 比值与 CRLF 形态抽验进闸门）
   - `26-10-31-2226-feat-webui-agg-content-map` —— 聚合读法机械化（模板/CSS/JS 内容定位走机器索引）

## 思考过程与决策

- **e2e 自检挂哪里**: commands 引擎对 `run` 列表逐条顺序执行、任一条非 0 即整任务 [FAIL]（引擎 run.py 实读）⇒ 自检脚本直接挂进 `dev.e2e` run 列表头部, 自检不过不进 spec; 另立 `dev.e2e-check` 可单独跑。端口单点沿用 `e2e/harness.mjs`（E2E_PORT || 8137）; 8099（人工桩惯用值）默认仅告警。归属判定不走 curl（HTTP_PROXY 下 curl 判据不可靠, smoke.md 已记）, 走 `Get-NetTCPConnection` + `Win32_Process.CommandLine`（命令行里带 clone 路径, 一眼看出别 clone 残留桩）。
- **doc-refs 机械化拆四处**: ①模板补占位（HTML `doc-refs` 空 meta / md `**Refs:**` 行）—— 人只填值; ②`_common.md_set_refs` 修「空值占位行不认」缺陷（原正则要求非空 `(.+?)`, 会对空占位另插一行 = 复发 8 的 md 版）; ③`gen_doc_map --check` 增重复声明检测（search()/dict(findall) 对重复 meta 静默塌缩, 复发 8 根因无机检）; ④新命令 `kb.ref`（set_doc_refs.py）: 回填认领链一条命令, 目标不存在即拒（拦「先回填后落盘」悬空窗口）, 原位改值（拦「另插一行」）。
- **写盘形态守卫阈值（全仓标定实测 2026-10-31）**: memory-bank 全部 md 中, 唯一 bytes-per-line<12 且 ≥100 行的是实证件（3.8）; 唯一裸 CR 是 `tasks/26-10-13-backend-seed-state-writeback.md` 头部 5 行 `\r  \n` 形态（本轮修掉, 字节级只删 CR）。守卫三查: 裸 CR / 同文件 CRLF+LF 混排 / 行数≥300 且 bytes-per-line<8; 实证件（逐字符一行, 无法无损复原行结构）进冻结豁免清单。
- **聚合映射落点**: dev 包新 task `dev.ui-map` + `scripts/ui_content_map.py`; 域分类按 frontend-split.md 的聚合口径（shell 内联段 / tpl 分片+挂载 shell / css 按 skin+link 序 / js 清单序）, 清单单点解析 shell 的 tpl-manifest。

## 实现计划

1. 复验四条 issue 锚点并把复验行写回 issue（本档案立档后立即做）。
2. e2e 自检: `scripts/e2e_selfcheck.py` + 挂 `dev.e2e`/新 `dev.e2e-check`。
3. 写盘形态守卫: 新测试文件三查 + 存量冻结清单; 顺手修存量裸 CR 件。
4. doc-refs 机械化: 模板占位 + md_set_refs 空值修复 + gen_doc_map 重复检测 + `kb.ref` 命令 + 守阵测试。
5. 聚合映射: `scripts/ui_content_map.py` + `dev.ui-map` task。
6. 回写: 四份坑档各补一行工具指针; issue 修复后补充 + 翻 Done; test.full + 基线切片; kb.wrap。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 立档 + 认领链（kb.new --refs D4 自动反向补链四条 issue） | Done(2026-10-31) |
| 2 | 复验四条 issue 并回写复验行 | Done(2026-10-31) |
| 3 | e2e 自检脚本 + dev.e2e/dev.e2e-check 挂接 | Done(2026-10-31) |
| 4 | 写盘形态守卫测试 + 存量处置 | Done(2026-10-31) |
| 5 | doc-refs 机械化（模板/写入器/闸门/kb.ref） | Done(2026-10-31) |
| 6 | 聚合内容映射脚本 + dev.ui-map | Done(2026-10-31) |
| 7 | 回写坑档指针 + issue 翻 Done + 基线切片 + kb.wrap | Done(2026-10-31) |

## 进度日志

### R0 · 立档 (2026-10-31)

- 会话开工同步 3d35d610→60044d07; 读四份 issue + 四份判据坑档 + R4 报告堆 3 立项段。
- 复验取证: e2e 无前置探测/dev.e2e run 仅 npx; gen_doc_map 对重复 meta 塌缩; 实证件 bytes-per-line=3.8 仍在且全仓无同类守卫; commands 无内容映射 task。
- 新发现并修: `tasks/26-10-13-backend-seed-state-writeback.md` 头部 5 行裸 CR（`\r  \n` 形态, 字节级只删 CR, 内容零变化）。
- 全部实现落码: e2e_selfcheck.py / ui_content_map.py / set_doc_refs.py / test_kb_writeform.py / test_kb_docrefs_tools.py + 三处 config 挂接 + 模板占位 + md_set_refs 修复 + gen_doc_map 重复检测。
- 验证: 新增守阵与受影响面守阵全绿 (数字见 testing/baselines/ 最新切片, commands run kb.baseline); dev.e2e-check 自检实测 (通过路径 + 占用失败路径); dev.ui-map 实测多域命中; kb.check 全绿。

- 2026-11-01 00:10 堆3四件 issue 认领并实施完成: e2e自检/写盘守卫/doc-refs机械化/ui-map 全部落码实测; 基线切片 26-11-01-0010
