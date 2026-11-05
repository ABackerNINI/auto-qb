# 配置键历史与已废除键 (外迁存档)

> 摘要: `keys.md` 中已废除键与历史迁移流的逐字原文 — `trackers.<站点>.hr_check` 旧键、config v4→v5 迁移明细。
> 触发: hr_check 旧键, trackers.hr_check, v4→v5 迁移, global_traffic_monitor 删除键, 配置键历史

## 已废除: `trackers.<站点>.hr_check`

> 原 `keys.md`「trackers 站点段」表格行, 逐字外迁; 现行键面见 `hr_check.sites.<档案 id>`。

| 键 | 必填 | 说明 |
|----|------|------|
| `hr_check` | | **旧键(已废除, 26-09-27-1930 起)**: 站点级在线核实的唯一入口是 `hr_check.sites.<档案 id>`。本键不再被任何代码接受 —— config v1→v2 迁移曾把它改写到新位置; **v3(config v2→v3)起出现即直接删除**(不再提供旧位置兼容)。站点接入键集见下节 |

## config v4→v5 迁移明细

> 原 `keys.md`「traffic_source 段」段尾, 逐字外迁。

**v4→v5 迁移**(计划 26-10-17-0339 S15): 曲线段内联 `traffic_source[].traffic_monitor.dat_path` 迁到本段 `traffic_monitor.dat_path`(曲线段内的 `traffic_source` 键删除); 旧顶层 `global_traffic_monitor` 段仅 `notify_cooldown_s` 保留到本段 `global_traffic_monitor.notify_cooldown_s`, 其余键(`enabled`/`tool_url`/`tool_token_path`/`subscribe`/`autostart`)与整段一并删除(逐键打 WARNING)。`provider` 按「旧 gtm 段非空 -> `global_traffic_monitor`, 否则 `traffic_monitor`」推导。并存期 TrafficMonitor 仅作对照读, **不得与工具同写一文件**(工具是历史文件的唯一写者)。
