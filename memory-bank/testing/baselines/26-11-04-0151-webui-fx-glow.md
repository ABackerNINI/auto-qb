# 5005 passed + 10 skipped(根); 覆盖 TOTAL 23327 stmts / 185 miss / 7956 branches / 158 partial / 99% —— fx 辉光四轮修入库前全量

> 摘要: fx 辉光四轮修入库前全量
> 基线时间: 2026-11-04 01:51
**Refs:** memory-bank/tasks/26-11-04-webui-fx-glow.md

## 验收数字

- `commands run test.full` 实测(2026-11-04 01:51): **5005 passed + 10 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 23327 stmts / 185 miss / 7956 branches / 158 partial / **99%**
- 口径注记: 中途两轮红均为本轮 KB 回写自身所致(①改档案未重建索引 → 6 条 structure 红, kb.index 后清零; ②任务档案 `**Refs:**` 空行被 TASK_REFS_RE 的 `\s*` 连换行吞掉、误把下一节标题当引用目标 → 认领链红, 填实双向链后清零), 非源码回归; 终态全绿如上。

## 本改动面

- `src/auto_qb/webui/static/shared/fx/fx.css`: 辉光供给面标量化(--fx-glow-ink/-a/-a-hi)+ `*` 通用层配色公式(--fx-glow-stack 四层: 硬芯 0blur + 正 spread 扩方三层)+ glow 原语改消费 stack
- `src/auto_qb/webui/static/shared/fx/fx-presets.css`: neon/glass/crisp/兜底四块改标量供给; glass ink=--accent-hi
- `src/auto_qb/webui/static/flux/css/fx-mount.css`: .bt 悬停合成改 stack; danger/danger-solid ink 重挂 --error; chip 改 stack
- `src/auto_qb/webui/static/fx/showcase.html`: 补 --accent-hi; force-glow 改标量; 镜像/ctl.on/hsp-glow/pc-sig-bar 对齐 stack
- `memory-bank/`: tasks/26-11-04-webui-fx-glow.md 新档; pitfalls/web-ui/css-var-substitution-level.md 新坑; 本切片
- 测试面: 零测试改动(静态 CSS/文档轮)
