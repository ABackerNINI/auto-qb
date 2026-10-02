# 基线 · 2291 passed + 3 skipped / 99% —— ESC 清筛选兜底收尾轮

> 摘要: 方案 A(退栈链终端兜底)实现 `0d286cc5`(阶段1)+ 桩服务走查 8/8 项 / 34 断言(阶段2)之后的收尾轮: 基线切片 / issue 26-10-01-2108 补收尾行 / 计划 26-10-02-1632 置 Done / 档案置 Done / progress 迁出 / browser-env 回写。档案: [tasks/26-10-02-webui-esc-clear-filters.md](../../tasks/26-10-02-webui-esc-clear-filters.md)。
> 基线时间: 2026-10-02 18:15, develop @ cfbfa712(干净树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2291 passed + 3 skipped / 99%**(13,259 语句 / 86 未覆盖 / 4,442 分支 / 81 partial,
test.full 38.3s, rc=0)。
相对上一切片(26-10-02-1744: 2291 passed + 3 skipped / 99%, @ 0d286cc5)passed/skipped/未覆盖/
分支/partial **全持平**, 唯语句 13,357 → 13,259(-98)。该 -98 与 1653→1705 两个纯文档轮之间的
-98(13,349 → 13,251)同型: 语句数呈高低两档轮替(高 13,349/13,357 ↔ 低 13,251/13,259), 而
`0d286cc5..HEAD` 经 `git diff -- '*.py'` 核实**零 .py 改动** —— 判为覆盖率语句数读数的轮次性
波动, 非代码差异; 此前两条切片把 -98 归因「基点移动」不成立(纯文档提交不增减 .py 语句)。
跨轮比较以 passed/skipped 与 99% 档位为准。
