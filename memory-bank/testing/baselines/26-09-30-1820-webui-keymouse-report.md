# 基线 · 1832 passed + 3 skipped / 90% —— WEBUI 键鼠割裂调研报告 (纯知识库轮)

> 摘要: 本轮只动知识库(报告 reports/26-09-30-1806 + tasks 档案追加 + activeContext 切片 +
> 5 份已完结切片蒸馏 + 索引重建), **源代码零变更**; 全量测试跑一遍核实知识库守阵
> (test_memory_bank / test_docs_forms)仍绿 —— 中途两红已就地消掉(切片数 71>70 触发蒸馏;
> 被蒸馏切片的一条引用改指坑档)。数字较上基线的 +3 全部来自上基线之后已入库的远端提交,
> 与本轮无关。
> 基线时间: 2026-09-30 18:26 (develop @ fa54f02b + 本轮 KB 文件, 待 ship.commit)
> 档案: tasks/26-09-28-webui-keyboard-shortcuts.md (子任务 #6)

TOTAL **1832 passed + 3 skipped / 90%**(12731 语句 / 1042 未覆盖 / 4344 分支 / 432 partial,
test.full 25.75s, rc=0) —— 较上基线 [26-09-30-1210](26-09-30-1210-dangerous-ops-layer.md)
(1829 passed + 3 skipped / 91%)净增 3, 全部来自 87f3437d..fa54f02b 间的已入库提交
(fa54f02b 本身无测试变更):

- tests/test_commands_engine.py **净 -2**(+4/-6; 31cda33d 引擎全文透传改造, 摘要族测试退役换新判据)
- tests/test_utils.py **+4**(1ae49716 打开目标文件夹资源管理器弹顶层修复)
- tests/test_web_shortcuts.py **+1**(865593dc 上下键长按连发)

覆盖率口径: 语句 12650→12731(+81)、未覆盖 1012→1042, 91%→90% —— 语句增量来自上述同批提交
(键鼠/引擎/打开路径), 非本轮(本轮零代码变更)。

## 本轮改动面(均为知识库文件)

- 新建 reports/26-09-30-1806-report-webui-keymouse-cohesion.html(键鼠割裂调研, 方案 B 推荐);
- tasks/26-09-28-webui-keyboard-shortcuts.md 追加子任务 #6 + 进度日志 + Refs 反链;
- activeContext 新切片 26-09-30-1808-webui-keymouse-cohesion + 同目录蒸馏删除 5 份已完结切片;
- 26-09-30-1007-commands-engine-self-stdio.md 一条引用改指 pitfalls/ops/console-encoding.md(被蒸馏切片的断链修复);
- `commands run kb.index` 重建 16 份索引。
- 合流 fa54f02b(热重载计划入档)后其认领链两处断链卡闸门, 随本轮一行级修复: 1751 计划 doc-refs
  补 `memory-bank/plans/` 前缀 + 1857 目标计划补反向声明(此前无 doc-refs 行)。
