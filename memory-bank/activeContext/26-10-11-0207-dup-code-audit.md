# 全仓重复代码审查 · 轮 05–10(core 全包)

> 摘要: 用户「做 Phase 1 core部分」→ 按计划 `26-10-10-2333` 执行 **Phase 1 后端 core 包 = 轮 05–10**(调度内核 / 数据接入 / 流量 / 领域 / 模块契约样板 / 模块业务, ~8.1k 行 / 32 文件)。**纯审查轮, 零源码改动**: 滚动报告 `26-10-11-0033` 追加 §08–§13 + 累计计数 §14; 累计 46 项发现(A21/B6/C9/D10); 入池 **core 9 条 refactor issue**(专题 `dup-code-audit`, 均 Open 未认领)。S2 提名实测: pylint R0801 对 core 0 命中(下探 =5 仅 1 组)、jscpd python 0 clone —— 与 config 同结论, 字面重复极低, 主战场是结构线索 + 精读。
> 最后活动: 2026-10-11 02:07

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md

## 正在进行

- **轮 05–10(core 全包)已完成**(纯审查轮, 零源码改动)。滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 已追加 R05–R10(§08–§13)+ 累计计数/候选排序(§14); 累计计数 A26/B7/C17/D19(config+core)。
- **core 9 条 refactor issue 已入池**(均 Open, 未认领): `core-conn-state-boilerplate-dup` / `core-module-contract-boilerplate-dup` / `core-traffic-store-read-write-dup` / `core-traffic-parse-diff-family-dup` / `core-modules-ops-grouping-boilerplate-dup` / `core-modules-tag-rules-sample-boilerplate-dup` / `core-day-key-prune-dup` / `core-speed-unit-convention-dup` / `core-episode-marker-dup`。
- **下一轮候选**: Phase 1 后端轮 11(hr 解析面 adapters·parse·bencode·fetcher); 或按用户偏好调整顺序。每轮开工另立会话, 按 S1–S6 走。

## 关键结论(供后续执行参考)

- **core 字面重复同样极低**: pylint R0801 对 core 0 命中(=8)、下探 =5 仅 modules/__init__ 1 组; jscpd python 0 clone。**core 的重复以「样板骨架」为主(A 类最多, 21 项)** —— 同一动作的多个实现(qbapi/模块)与「同源已演化」(traffic 解析/差分、集数正则)次之。
- **A 类重灾(可提取, 收益高/风险低)**: qbmanager 连接节流/重连成功/state 加载样板(R05-M01..M03); ModuleHost hook 分发(R05-M04); traffic_store 读解析 4 处两两同构 / 追加建头 2 处 / build_grid 分支 2 处(R07-T01..T03); 模块内业务样板一批(R10-G01/G02/O01/O02/D01/D02/R01/R02/T01..T03)。
- **C 类已定位**: ①速度单位「KiB↔bytes + 0=不限速」多处且**取整方向分歧**(qbapi floor vs curves 向上); ②**state 日键淘汰口径三处形态各异**(state keep-N-days + 值比较 / speed_curve keep-N-days + 键比较 / ops skip_check_day 只留当日); ③集数「分辨率/年份排除集」episodes↔tvshows 同值两份; ④v3 遗留 8 列 agg 行兜底分支(与 v4 换代「不设双读」声明相悖); ⑤原子整文件重写口径 traffic_store 自实现 ↔ infra.utils.atomic_write 同族(归轮 18)。
- **B 类(只登记, 不急合)**: traffic day↔agg 解析骨架、差分两实现、加权聚合两实现; 集数正则族(episodes 4 项 vs tvshows 7 项, 超集已演化); 站点优先/全局回落判定(maintenance ↔ hr)。
- **契约层专项**: 模块 `apply` 段相等短路样板 + 全局任务自注册样板(R09-C01/C02)—— 收益高但触契约层, 建议专项并联动 P0 守阵。

## 后续候选(未开工)

- 轮 11–19(hr / webui / rules / infra / torrents+tray)、Phase 2 前端(20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(26)。
- 轮 26 汇总: 重构候选排序表(报告 §14 已有雏形)+ 跨层「同一事实」总账 + 未入池候选(原子写收敛 R07-T05·R05-S01 / 相位认领 R09-C03 / B 类)按清偿顺序入池。