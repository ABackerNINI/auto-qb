# 基线 · 1767 passed + 3 skipped / 91% —— cap 翻倍 + list 平铺轮 (守阵常量/文案改动, 零用例增删)

> 摘要: 用户定调治「提交触 cap 多轮返工」的 token 税 —— `CAP_POLICY` 全表×2(AGENTS.md 8000 例外),
> 触顶处置统一「削到最大值 50%」(`LOG_ROTATE_KEEP`→`TRIM_KEEP=1/2`); `commands list` 改完全平铺。
> 改动面: 守卫常量与提示文案、SKILL/镜像文档、引擎 `_tree.py`/`run.py`/`_config.py`、`gen_tasks_index`
> 头文案(24→48 KB, `tasks/_index.md` 随之重建一次)。全流程: 同步 42502f29 开工 → 收尾前再同步 58d72e0a
> (远端 WebUI 新提交快进) → test.full 复测。
> 基线时间: 2026-09-30 00:18 (develop @ 58d72e0a, 合并远端后复测)
> 档案: tasks/26-09-30-memory-bank-token-budget.md

TOTAL **1767 passed + 3 skipped / 91%**(12396 语句 / 999 未覆盖 / 4208 分支 / 410 partial, test.full 20.2s, rc=0)
—— 与上基线 26-09-29-2317 **完全持平**(本轮零用例增删; 守卫数字断言读的是 `_common` 常量, 翻倍不产生新红/新绿)。
6 条 warnings 为既有依赖级告警(starlette testclient 等), 与本轮无关。分路机检: 引擎+包 test.pkg 72 passed;
memory-bank 守卫 24 passed(test.one -n 0); doc.caps / kb.check / doc.links 全绿,
AGENTS.md 7,966/8,000(余量 34)。
