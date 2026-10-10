# 全仓重复代码审查(分步执行计划)

> 摘要: 用户要求「做一轮重复代码审查, 主要用于后续重构, 增强一致性与减少维护点; 先写一个分步执行方案, 步骤拆细, 避免单轮任务过长」, 并在追问下选定**正式 HTML 计划 + 全仓范围(含前端三皮肤)+ 步骤拆细**。本轮**只产出计划制品, 零代码改动**: 计划 `plans/26-10-10-2333-plan-dup-code-audit.html`(专题 `dup-code-audit`, 状态 `Open` 待拍板)。计划含①唯一判定词表四类 —— A 真重复(可提取) / B 分歧重复(只登记不急合) / C 同一事实多表示(单点违反, 收益最高) / D 表面相似(明确不动, 防过度抽象); ②方法与工具(两段式: 机器提名 pylint R0801 + jscpd, `uv run --with` 临时环境不改依赖 → 人工按符号清单精读定性; 叠加结构线索 grep 补语义重复); ③**27 轮分步清单**(Phase 0 准备 → Phase 1 后端 19 轮 → Phase 2 前端 4 轮 → Phase 3 测试与横切 2 轮 → Phase 4 汇总), 一轮一个面、独立会话, 按「重复密度 × 读取代价」排序(先 config, 因其为 C 类最密的包); ④每轮固定六步微步骤 S1–S6; ⑤硬停手点(只审查不改码 · 单轮 ≤4000 行 · B 类只登记)。命中立档阈值, 已立档 `tasks/26-10-10-backend-dup-code-audit.md`。
> 最后活动: 2026-10-11 00:33

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md

## 正在进行

- **Phase 0 + 轮 01–04(config 全包)已完成**(用户拍板范围; 纯审查轮, 零源码改动)。滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 已追加 R00–R04; 分类计数 A5/B1/C8/D9; 入池 **7 条 refactor issue**(专题 `dup-code-audit`, 均 Open 未认领)。
- **下一轮候选**: Phase 1 后端轮 05(core 调度内核 qbmanager·taskqueue·state·module); 或按用户偏好调整顺序。每轮开工另立会话, 按 S1–S6 走。

## 关键结论(供后续执行参考)

- **工具提名近乎静默**: pylint R0801 全 src 仅 2 组(均 torrents)、config 0; jscpd 全 src python 0 clone。**config 的重复是 C 类(同一事实多表示), 不是复制粘贴** —— 印证计划预判; 主战场是 grep + 逐文件精读。
- **C 类已定位的重灾**: ①配置键面在 schema/validation/models/loaders/writer/docs(2 处)/keys.md 共 8 处表示, **docs 两处无守卫且已漂移**(hr_check 键数 7/8/9); ②枚举常量 schema↔validation 双份 + STATE_ATTRS 三份 + `MAINTENANCE_TAG_MODES` 死件; ③默认值 models/schema/docs 多源(log.format 已漂移)。
- **A 类可动项**: writer 备份复制块(jscpd 命中)、端口校验三处、时间窗解析两套、`_get` 被两处绕过、页面事实字面量、点路径删除工具。
- **与既有审查不重叠**: 全项目 Code Review(`26-10-05-0951`)查缺陷/安全/边界; 本专题查结构重复。变异审计(专题 `mutation-audit`)管「测试够不够硬」, 本专题管「代码要不要合并」。

## 后续候选(未开工)

- 轮 05–19(core / core-modules / hr / webui / rules / infra / torrents+tray)、Phase 2 前端(20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(26)。
- 轮 26 汇总: 重构候选排序表(报告 §08 已有雏形)+ 跨层「同一事实」总账 + 未入池候选(点路径工具 R03-G01 / 段认领 R03-I01·K01 / B 类 R03-L02)按清偿顺序入池。