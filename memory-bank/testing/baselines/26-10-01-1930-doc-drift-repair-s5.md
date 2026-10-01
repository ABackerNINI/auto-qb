# 基线 · 1909 passed + 3 skipped / 91% —— 文档漂移修复 S5 收尾(P3 清扫, 纯文档)

> 摘要: 文档漂移分段修复(plans/26-10-01-1728-plan-doc-drift-repair.html)S5 收尾基线。
> 本段只改 memory-bank 文档(projectbrief / progress/roadmap / modules/rules-and-deps 计数实测刷新)
> + 删 src/auto_qb/mixins/__pycache__ 未跟踪残留(git 零跟踪), **零代码零测试变更** ——
> 通过数与 L1-L3 基线 26-10-01-1835 持平为预期。
> 基线时间: 2026-10-01 19:30, develop @ 7f046ca0(S4 已提交, 工作树含 S5 文档改动未提交)。

TOTAL **1909 passed + 3 skipped / 91%**(13278 语句 / 1051 未覆盖 / 4408 分支 / 435 partial,
test.full 31.2s, rc=0)—— 通过数与审计 L1-L3 基线 26-10-01-1835 **持平**(纯文档零新例零删例);
覆盖率数字同口径(91%, 语句数一致; 未覆盖/partial 的 ±3/±1 为逐轮采样浮动, 结论不变)。
机检三连同轮全绿: kb.index 已生成 16 个索引; kb.check 256 文档 / 159 专题无缺主键
(切片数 81>70 与 cap 债务 1 项为既有债务, 不拦提交); doc.links 绿。

## 本段改动面(纯 memory-bank + 未跟踪产物)

- P3 计数清扫(逐条对代码实测): projectbrief.md 15→13 条件; progress/roadmap.md 16→13 条件;
  modules/rules-and-deps.md base.py 274→314 / expr/ ~700·6 文件→1245·7 文件(含 __init__ 46)/
  actions/ 934→673 / full_checking 178→152(S3 沿用旧文未复测的两处一并校正)。
- 豁免未动(有快照披露头注, 按 plans/26-10-01-1728 §4-S5 既例): productContext.md(内容基线
  2026-09-05)/ modules/overview.md 与 core-domain.md(行数为 2026-09-05 快照)/ core-runtime.md
  (快照口径以行内标注为准)/ mixins.md(历史快照)/ webui-static-contract.md 与 core-config.md
  (26-10-01 实测已标)/ conventions/code-style.md(无残留计数断言)。
- 顺手项: 删 src/auto_qb/mixins/(仅 __pycache__, 26-10-01-1835 基线删过一次后被测试进程再生,
  再次确认 git 零跟踪后删除)。
- 代码注释残留 4 处(core/state.py docstring / qbmanager.py:398 / webui/runtime.py:237 /
  core/mixins/__init__.py 已随 L2 删除故实存 3 处)按计划 §6 待用户拍板, 本段未动任何 .py。

**Refs:** memory-bank/plans/26-10-01-1728-plan-doc-drift-repair.html · 滚动档案
memory-bank/tasks/26-10-01-docs-doc-drift-repair.md
