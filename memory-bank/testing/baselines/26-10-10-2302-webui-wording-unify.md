# 3111 —— WEBUI 文案对齐 qB 全量排查报告(不改代码)基线

> 摘要: 用户要求把 WEBUI 文案统一到 qB 口径并要求"全面排查"(例证:「做种」qB 叫「做种数」)。本轮**只摸底、只出报告, 零代码改动**: 以本机 qBittorrent 源码官方 zh_CN 译文为基准(`src/webui/www/translations/webui_zh_CN.ts` 为主 + `src/lang/qbittorrent_zh_CN.ts` 交叉), 对 `shared/` 面向用户的中文文案逐概念域对照。产出报告 `reports/26-10-10-2237-report-webui-wording-unify.html`(6 概念域: 列头字段 / 状态词 / 动作菜单 / 传输方向词 / 对端状态词 / 保持不动与自有概念), 约 32 条需改术语 + ~50 处方向词字面改点 + 5 处对端状态词, 涉 16 个 shipped 文件。关键结论: qB 无「上行/下行」一律「上传/下载」;「取流/供流」为自造词且同语义 6 种叫法; qB **WebUI 与 GUI 译文在个别词上不一致**(Seeds: WebUI 种子 / GUI 做种数)须先选边; 我方状态词系统性多加「中/已」且自身不统一。报告列 6 个决策点待拍板, 未动任何生产文件。命中立档阈值(产出报告制品), 已立档 `tasks/26-10-10-webui-wording-unify.md`。
> 基线时间: 2026-10-10 23:02

**Refs:** memory-bank/tasks/26-10-10-webui-wording-unify.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `e4282642`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows; 起跑时等 `.venv` 排他锁约 2.6s —— 环境侧长驻 `uv` 进程占用, 非本仓问题)
- **实测 (Windows)**: **3111 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 70.9s, 其中跑测 68.27s)
- 增量明细(本轮真正新增, **全部是文档/知识库件, 无 `src/` 与 `tests/` 改动**):
  - `memory-bank/reports/26-10-10-2237-report-webui-wording-unify.html`(单文件 dark HTML 报告 + `doc-refs`)
  - `memory-bank/tasks/26-10-10-webui-wording-unify.md`(立档)
  - `memory-bank/activeContext/26-10-10-2302-webui-wording-unify.md`(会话切片)
  - `memory-bank/reports/_index.md` + `memory-bank/tasks/_index.md`(索引重建)
  - 本基线切片
- 已复核的机检(本轮相关): `test_docs_forms.py` 11 passed(报告 meta / 命名 / dark 主题 / 索引自洽); 提交闸门另跑 `gen_*_index --check` + `gen_doc_map --check`(认领链)+ `timekit --check`。
- 未纳入本轮(刻意不越界): 任何文案改动、守阵同步、`resources/detail-panel-templates/` 与后端 schema help/docs 的同步 —— 全部待报告 §10 的 6 个决策点拍板后另立计划执行。
