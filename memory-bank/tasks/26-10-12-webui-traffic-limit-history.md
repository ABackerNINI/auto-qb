# 26-10-12-webui-traffic-limit-history — qB 流量图限速线按当时值分段

**Status:** Open
**Added:** 2026-10-12
**Updated:** 2026-10-12 06:19
**Topics:** webui-traffic-limit-history
**Summary:** 用户命题「流量图限速线显示当前限速值有误导性, 需保存限速更改体现当时的限速, 先写计划, 使用 grilling 技能」。grilling 一轮七问收敛: 记生效值不记曲线目标 / 采样点变化才记 / 前端分段画(各段各区间, 末段到 now, 可见性判据逐段化) / 缺记录不画不回填 / 三挂点与变体维持现状 / 悬停读数增补; D3 用户两轮裁定终值 = **分天保存**(`qb-traffic-v4/limits/<日期>.dat`, 00:00 硬切 + 新天基线 carry, 不淘汰与 day/month 全保留对齐, 无配置键)。追问「不分天吗 / 缺数据区怎么界定 / 保存几年怎么办」推动补强: 读侧 mtime+size 解析缓存、缺数据区界定规则(阶梯函数恒有值, 唯一缺区 = 记录起点前; 停机时刻误差 ≤ 停机时长)、病态翻转常量告警护栏。计划 26-10-12-0535 Open, W1 后端 / W2 前端 / W3 收尾待实施; 纯文档轮零代码, 数字见 `commands run kb.baseline`。
**Refs:** memory-bank/plans/26-10-12-0535-plan-webui-traffic-limit-history.html,memory-bank/testing/baselines/26-10-12-0619-webui-traffic-limit-history-plan.md,memory-bank/activeContext/26-10-12-0619-webui-traffic-limit-history.md

## 原始请求

用户原文: 「目前的流量图中显示的限速线是当前的限速值, 有一定误导性, 需要保存限速更改, 体现当时的限速, 先写一份计划, 使用grilling技能」。

## 思考过程与决策

- **现状取证**: 限速线 = `qb_traffic_chart.js` `_qbDrawLimits` 用拉取响应那一刻的 `speedLimitBytes`(单点 `dialogs.js`, 即 `server_state.dl_rate_limit / up_rate_limit`)画满整窗; 限速变化源 = 限速曲线模块每轮查档写 qB(`speed_curve_mod.py`)+ WebUI 手动覆盖 + 备用限速切换; 主循环采样点 `_sample_global` 每轮已拿完整 `server_state`, 记录挂点现成。
- **grilling 七问**(第一轮全前沿一次问齐): D1 记生效值(不记曲线目标——手动保护跳过时目标未写进 qB, 记了是新失真) / D2 采样点变化才记(单线程黄金法则 5、零新增请求、覆盖一切变化源含 qB 原生界面手改) / D3 存储与保留 / D4 前端分段画 / D5 缺区不画不回填 / D6 三挂点 + 变体 13/14/15 维持现状 / D7 悬停读数。用户裁定「其它按推荐」+ D3 修订; 第二轮前沿为空, 收敛。
- **D3 两轮修订**: 初裁「独立文件 + 配置键 90d」→ 用户改「目录与流量数据一致、不加配置键、保留对齐流量图最大保存时间」→ 追问轮(不分天吗 / 缺数据区 / 保存几年)后终裁「**分天保存**」。分天形态: `qb-traffic-v4/limits/<YYYY-MM-DD>.dat`(日期格式单点 `V4_DATE_FORMAT`), 00:00 硬切 + 新天首行基线 carry(单天文件自洽, 读侧拼接不回溯前一天), `limits/` 非系列目录(`v4_rel_dir_to_key` 只认 `global/` 与 `torrents/<hash>`)系列淘汰天然跳过。
- **「保存几年」防御**: 读侧 mtime+size 键控解析缓存(照 `V4DayCache` 形状, 文件没变零解析) + 病态翻转常量告警(照 `_BAD_LINE_WARN_*` 先例, 只告警不删数据——删了违背对齐语义); 正常密度三年千余条 ≈ 百 KB 级, 各层量级核算在计划 §5。
- **缺数据区界定**: 限速是阶梯函数, 记录起点后每个时刻恒有生效值(0 = 不限速也是值), 内部无缺口; 唯一缺区 = 记录起点之前(不画线即「当时值未知」的诚实表达); 停机/写失败窗口内变化的事件时刻误差 ≤ 停机时长(值不丢, 恢复首轮基线补上, 图上不标注)。
- **不推翻 26-10-08 拍板**(任务档案 26-10-08-webui-qb-traffic-yaxis-annotation): 限速取 qB 全局限速、上下载各一条、自动模式峰值超限才画——本计划只改「取值方式」(单值 → 分段历史), 其余判据全部延续。

## 实现计划

见 [计划 26-10-12-0535](../plans/26-10-12-0535-plan-webui-traffic-limit-history.html) §3 方案设计 / §4 波次与验收: W1 后端(`core/traffic_limits.py` 记录器 + 读侧 + `traffic_sample_mod` 接线 + `traffic_qb.py` payload 扩展) → W2 前端(`_qbDrawLimits` 分段化 + 快路暂存 + `_qbHoverOf` 悬停读数 + node 电池红验) → W3 收尾(基线切片 + 文档回写 + 真机走查)。

## 子任务状态表

| 波次 | 内容 | 状态 |
|---|---|---|
| W1 | 后端: 记录器 + 读侧 + payload 扩展 | 待做 |
| W2 | 前端: 分段线 + 悬停读数 + 守阵 | 待做 |
| W3 | 收尾: 回写 + 真机走查 | 待做 |

## 进度日志

- 2026-10-12 05:35 计划成文(26-10-12-0535, Open), grilling 七问拍板记录入档(§2)。
- 2026-10-12 06:13 D3 二次裁定分天保存, 计划同文件修订(读侧解析缓存 / 缺数据区界定 / 病态翻转护栏随轮补强, 验收判据扩充)。
- 2026-10-12 06:19 收尾入库: 纯文档轮(计划 + 本档案 + 活跃切片), 零代码零测试改动, 实测数字见 `commands run kb.baseline`; 环境备忘: PowerShell 下 `git grep` 中文输出显示乱码(仅显示层, 文件无损), 查 CJK 内容改用 read 工具直读。
